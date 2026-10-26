from pathlib import Path
from typing import Optional

from fluent_compiler.bundle import FluentBundle
from fluentogram import TranslatorHub, FluentTranslator


class TranslationLoader:
    def __init__(self, locales_folder: Path):
        self.locales_folder = locales_folder

    def get_content(self, locale: str) -> Optional[str]:
        with open(self.locales_folder / f"{locale}.ftl", "r") as f:
            return f.read()


class FluentService:
    def __init__(self, loader, locales_map):
        self._hub: Optional[TranslatorHub] = None
        self.loader = loader
        self.locales_map = locales_map

    @property
    def hub(self):
        if not self._hub:
            self._hub = TranslatorHub(
                self.locales_map,
                translators=[
                    FluentTranslator(
                        locale="ru",
                        translator=FluentBundle.from_string(
                            "ru-RU", self.loader.get_content("ru"), use_isolating=False
                        ),
                    ),
                ],
                root_locale="ru",
            )
        return self._hub

    def get_translator_by_locale(self, locale):
        if locale not in self.locales_map:
            raise ValueError(f"Unknown locale: {locale}")
        return self.hub.get_translator_by_locale(locale)


def configure_fluent(locales_path: str):
    locales_map = {
        "ru": ("ru", )
    }
    loader = TranslationLoader(Path(locales_path))
    return FluentService(loader, locales_map)
