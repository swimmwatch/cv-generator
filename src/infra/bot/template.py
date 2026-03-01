"""
Telegram Bot service template utilities.
"""

import gettext
import re
import typing
from pathlib import Path

import emoji
import jinja2

from infra.defaults import SUPPORTED_LOCALES
from utils.lang import DEFAULT_LANG_CODE
from utils.telegram.html import mention_html

GettextFunction = typing.Callable[[str], str]


class TelegramTemplate:
    __GETTEXT_LOCALES: dict[str, GettextFunction] = {}

    def __init__(self, template_dir: Path, babel_domain: str, babel_locale_dir: Path) -> None:
        self._template_dir = template_dir
        self._babel_domain = babel_domain
        self._babel_locale_dir = babel_locale_dir
        self._template_loader = jinja2.FileSystemLoader(searchpath=self._template_dir)
        self._template_env = jinja2.Environment(  # noqa: S701
            loader=self._template_loader,
            trim_blocks=True,
            lstrip_blocks=True,
            extensions=["jinja2.ext.i18n"],
        )

        self.__init_gettext_locales()

    def __init_gettext_locales(self):
        for locale in SUPPORTED_LOCALES:
            self.__GETTEXT_LOCALES[locale] = self.__make_gettext(locale)

    def __make_gettext(self, locale: str | None = None) -> GettextFunction:
        if not locale:
            locale = DEFAULT_LANG_CODE

        translation = gettext.translation(
            self._babel_domain,
            self._babel_locale_dir,
            [locale],
        )

        return translation.gettext

    @staticmethod
    def _prettify(rendered: str) -> str:
        rendered = rendered.replace("<br>", "\n")
        rendered = re.sub(" +", " ", rendered).replace(" .", ".").replace(" ,", ",")
        rendered = "\n".join(line.strip() for line in rendered.split("\n"))
        rendered = rendered.replace("{FOURPACES}", "    ")
        rendered = emoji.emojize(rendered)
        return rendered

    def _get_gettext(self, locale: str | None = None) -> GettextFunction:
        if locale is None:
            locale = DEFAULT_LANG_CODE

        default = self.__GETTEXT_LOCALES[DEFAULT_LANG_CODE]
        return self.__GETTEXT_LOCALES.get(locale, default)

    def render(self, template_name: str, locale: str | None = None, **kwargs) -> str:
        local_gettext = self._get_gettext(locale)
        template = self._template_env.get_template(
            template_name,
            globals={
                "_": local_gettext,
                "mention_html": mention_html,
            },
        )
        content = template.render(locale=locale, **kwargs).replace("\n", " ")
        return self._prettify(content)

    def inline(self, text: str, locale: str | None = None, **kwargs) -> str:
        local_gettext = self._get_gettext(locale)
        result = local_gettext(text)

        # pass template arguments
        if kwargs:
            result %= kwargs

        return result

    def render_error(self, content: str, locale: str | None = None) -> str:
        text = self.inline(content, locale)
        return self.render("error/inline.html", locale, content=text)
