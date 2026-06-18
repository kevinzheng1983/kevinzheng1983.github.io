# kevinzheng1983.github.io

## Local preview

This project uses Ruby 3.3 and the GitHub Pages Jekyll dependency set.

Install dependencies once:

```bash
PATH="/opt/homebrew/opt/ruby@3.3/bin:$PATH" bundle install
```

Start the local site with live reload:

```bash
bin/jekyll serve --livereload
```

Then open <http://127.0.0.1:4000/>.

Build without starting a server:

```bash
bin/jekyll build
```
