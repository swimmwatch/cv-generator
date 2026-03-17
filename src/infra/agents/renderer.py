import gettext
from pathlib import Path

import jinja2
from weasyprint import HTML

from infra.agents.schemas.resume import ResumePayload
from infra.defaults import BASE_INFRA_BOT_DIR
from infra.defaults import SUPPORTED_LOCALES
from utils.lang import DEFAULT_LANG_CODE

_CV_TEMPLATE_DIR = BASE_INFRA_BOT_DIR / "templates" / "cv"


class ResumeRenderer:
    def __init__(self, babel_domain: str, babel_locale_dir: Path) -> None:
        self._babel_domain = babel_domain
        self._babel_locale_dir = babel_locale_dir
        self._env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(_CV_TEMPLATE_DIR)),
            autoescape=jinja2.select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
            extensions=["jinja2.ext.i18n"],
        )
        self._gettext_funcs: dict[str, gettext.GNUTranslations] = {}
        self._init_translations()

    def _init_translations(self) -> None:
        for locale in SUPPORTED_LOCALES:
            self._gettext_funcs[locale] = gettext.translation(
                self._babel_domain,
                self._babel_locale_dir,
                [locale],
            )

    def render_pdf(self, payload: ResumePayload, locale: str | None = None) -> bytes:
        locale = locale or DEFAULT_LANG_CODE
        translation = self._gettext_funcs.get(locale, self._gettext_funcs[DEFAULT_LANG_CODE])
        self._env.install_gettext_translations(translation)  # type: ignore[attr-defined]

        template = self._env.get_template("index.html")
        rendered_html = template.render(resume=payload.model_dump(), locale=locale)

        return HTML(
            string=rendered_html,
            base_url=str(_CV_TEMPLATE_DIR),
        ).write_pdf()
