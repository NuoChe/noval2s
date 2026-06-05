"""Cross-chapter entity registry with deduplication."""

from __future__ import annotations

import re
import unicodedata

from novel2script.models.enums import IntExt, WarningCode, WarningSeverity
from novel2script.models.schema import Character, CharacterDraft, Location, LocationDraft, Warning


def _slugify(name: str, prefix: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name)
    ascii_name = ascii_name.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")
    if not slug:
        slug = str(abs(hash(name)) % 100000)
    return f"{prefix}_{slug}"


class EntityRegistry:
    def __init__(self) -> None:
        self.characters: dict[str, Character] = {}
        self.locations: dict[str, Location] = {}
        self._name_to_char_id: dict[str, str] = {}
        self._name_to_loc_id: dict[str, str] = {}
        self.warnings: list[Warning] = []

    def _resolve_char_id(self, draft: CharacterDraft) -> str:
        names = [draft.name] + draft.aliases
        for name in names:
            if name in self._name_to_char_id:
                return self._name_to_char_id[name]
        if draft.id:
            return draft.id
        return _slugify(draft.name, "char")

    def _resolve_loc_id(self, draft: LocationDraft) -> str:
        if draft.name in self._name_to_loc_id:
            return self._name_to_loc_id[draft.name]
        if draft.id:
            return draft.id
        return _slugify(draft.name, "loc")

    def merge_characters(self, drafts: list[CharacterDraft]) -> None:
        for draft in drafts:
            char_id = self._resolve_char_id(draft)
            if char_id in self.characters:
                existing = self.characters[char_id]
                merged_aliases = list(
                    dict.fromkeys(existing.aliases + draft.aliases + [draft.name])
                )
                merged_aliases = [a for a in merged_aliases if a != existing.name]
                if merged_aliases != existing.aliases:
                    self.warnings.append(
                        Warning(
                            code=WarningCode.CHARACTER_MERGED,
                            message=f"Merged aliases for character '{existing.name}': {merged_aliases}",
                            severity=WarningSeverity.INFO,
                        )
                    )
                self.characters[char_id] = existing.model_copy(
                    update={"aliases": merged_aliases}
                )
            else:
                self.characters[char_id] = Character(
                    id=char_id,
                    name=draft.name,
                    aliases=[a for a in draft.aliases if a != draft.name],
                    description=draft.description,
                )
            for name in [draft.name] + draft.aliases:
                self._name_to_char_id[name] = char_id

    def merge_locations(self, drafts: list[LocationDraft]) -> None:
        for draft in drafts:
            loc_id = self._resolve_loc_id(draft)
            if loc_id not in self.locations:
                self.locations[loc_id] = Location(
                    id=loc_id,
                    name=draft.name,
                    int_ext=draft.int_ext if isinstance(draft.int_ext, IntExt) else IntExt(draft.int_ext),
                    description=draft.description,
                )
            self._name_to_loc_id[draft.name] = loc_id

    def characters_list(self) -> list[Character]:
        return list(self.characters.values())

    def locations_list(self) -> list[Location]:
        return list(self.locations.values())

    def characters_json(self) -> str:
        import json

        return json.dumps(
            [c.model_dump(exclude_none=True) for c in self.characters_list()],
            ensure_ascii=False,
        )

    def locations_json(self) -> str:
        import json

        return json.dumps(
            [loc.model_dump(exclude_none=True) for loc in self.locations_list()],
            ensure_ascii=False,
        )
