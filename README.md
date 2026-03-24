# CV Generator Bot

> A Telegram bot that tailors your resume to any job posting using AI.
> Course project — [github.com/swimmwatch/cv-generator](https://github.com/swimmwatch/cv-generator)

---

## Documentation

| Language | Link |
|---|---|
| 🇬🇧 English | [docs/README.en.md](docs/README.en.md) |
| 🇷🇺 Русский | [docs/README.ru.md](docs/README.ru.md) |

---

## Quick Start

```bash
git clone https://github.com/swimmwatch/cv-generator.git
cd cv-generator
cp .env.example .env && cp .env.local.example .env.local
# Fill in OPENAI_API_KEY, TG_BOT_TOKEN, TG_WEBHOOK_URL in .env
make up
make migrate
```

See the full documentation in your preferred language above.
