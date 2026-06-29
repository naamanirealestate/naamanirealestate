# naamanirealestate

Static single-page site for Naamani Real Estate, served by Rack + Puma on Heroku.

## Run locally

```bash
bundle install
rackup
```

Open http://localhost:9292

Or with Puma directly:

```bash
bundle exec puma -t 1:1
```

## Deploy to Heroku

Confirm you want to deploy, then:

```bash
git push heroku main
```

(or `git push heroku master` if that's your branch)

Uses the Ruby buildpack. One web dyno; no database or add-ons required.
