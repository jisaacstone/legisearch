The website is static, but it requires generated json files to run.

The json can be generated locally with the legisearch tool.
Or you can download them from my website.

``` bash
cd static_web
wget "https://www.jisaacstone.com/projects/jurisdictions.json"
for jj in mountainview sanjose sunnyvaleca bart; do
  for ii in events items bodies; do
    wget "https://www.jisaacstone.com/projects/${jj}.${ii}.json" -O "${jj}.${ii}.json"
  done
done
```

After the json files are in the `static_web` directory, you can run any http server to test.
For example to run with the builtin python3 http server:

``` bash
cd static_web
python3 -m http.server
```

And the site will run at `localhost:8000`.
