#### Example Litestar app 

- Example litestar app using vite with gunicorn in production mode, not hot reload

* litestar
* vite
* litestar-vite-plugin
* jinja
* gunicorn
* typescript


### Build the frontend
```
cd frontend
npm run build
```

### Python3 env
```
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
gunicorn app.main:app -c gunicorn_conf.py
```

* in web browser load http://0.0.0.0:8000/
You should see:
```
Hello from Jinja2 + Vite + Litestar!
This content is powered by Vite + TypeScript! (test.ts added this)
```

```
jinja
├── README.md
├── app
│   ├── main.py
│   ├── static
│   │   └── assets
│   │       └── test.CWSp4QcS.js
│   └── templates
│       └── index.html
├── frontend
│   ├── index.html
│   ├── package-lock.json
│   ├── package.json
│   ├── public
│   │   └── vite.svg
│   ├── src
│   │   ├── counter.ts
│   │   ├── main.ts
│   │   ├── style.css
│   │   ├── test.ts
│   │   ├── typescript.svg
│   │   └── vite-env.d.ts
│   ├── style.css
│   ├── tsconfig.json
│   └── vite.config.ts
├── gunicorn_conf.py
├── package-lock.json
├── public
│   ├── assets
│   │   └── test.CWSp4QcS.js
│   └── manifest.json
└── requirements.txt
```
