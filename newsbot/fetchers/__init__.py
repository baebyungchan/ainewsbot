"""Source fetchers. Each returns list[Item] and never raises for a single bad entry."""

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
BOT_UA = "AINewsBot/1.0 (+https://github.com; personal news bot)"
