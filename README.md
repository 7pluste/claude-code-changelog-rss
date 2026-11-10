# Claude changelog feeds, with the content where your reader can see it

Anthropic's official feeds:

- Claude Code: https://code.claude.com/docs/en/changelog/rss.xml
- Claude Platform (API/SDKs/Console): https://platform.claude.com/docs/en/release-notes/feed.xml

The Claude Code one puts the change list only in `content:encoded`, which Slack, Outlook, Mattermost
and many email-digest readers ignore. This repo re-publishes both feeds hourly with the full
list in `<description>` too.

## Setup (about two minutes)

1. Create a new GitHub repo (e.g. `claude-feeds`) and push these files to `main`.
2. In the repo: **Settings → Pages → Source: GitHub Actions**.
3. **Actions → Rebuild Claude feeds → Run workflow** once (it also runs hourly after that).
4. Subscribe to:
   - `https://<you>.github.io/claude-feeds/claude-code.xml`
   - `https://<you>.github.io/claude-feeds/claude-platform.xml`

## Mattermost / plain-text readers

If bullets show up as raw `<ul><li>` tags, add `--plain` to the `python rewrite_feeds.py`
line in `.github/workflows/feeds.yml`. The description then becomes one `•` bullet per line.

## Run locally

```
python rewrite_feeds.py --out docs           # HTML descriptions
python rewrite_feeds.py --out docs --plain   # plain-text descriptions
```

No dependencies beyond Python 3.10+.
