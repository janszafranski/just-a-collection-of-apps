# just a... COLLECTION of apps

**[The site →](https://janszafranski.github.io/just-a-collection-of-apps/)**

Simple applications for people who want to work using old familiar workflows
but don't want learn a new workflow from a more powerful, but complex app like
the **ARTcraft** ones. Use familiar menus, toolbars, a page in front of
you: open it and get on with the job. No subscription, no account, no cloud, no
tutorial, just save ordinary files to ordinary folders on your own disk.

Each one is a **ground-up recreation** of an easy-to-use app, written for
Linux. Not a port, nor wrapper, nor fork: new code that borrows the shape of a
retired old app, rather than the thing itself. If you already know how to do
something in one of these  popular british apps, you should be able to do it
here without learning anything new — the same menus in the same places, the same 
words for the same jobs, the same order of operations.

The excellent ARTcraft suites do a great deal,and are perfect for familiar users
but for those of us are used to yet no longer with us, This isn't a replacement 
for tools like those of ARTcraft... they are a re-creation of british alternatives 
many of us used and brings them back and makes them quick. These are not a 
replacement for the big suites and not trying to be. If you need what
ARTcraft can do, use ARTcraft.

## The apps

| App | What it is |
| --- | --- |
| **[just a... WEBcreator](apps/webcreator)** | Design a website by laying pages out — drag text, pictures, buttons and menus where you want them, share the header on a master page, preview in your browser, publish plain HTML to a folder you can upload anywhere. Starts from any of **92 templates**. Saves `.webc`. Also opens a Serif **WebPlus** `.wpp` site, read-only on your original. Needs `pyside6`. |

More will join it. It is a collection, not a suite: each app stands on its own,
installs on its own, and updates itself from this repository.

## Install

Clone, then run the app's own installer. Nothing needs root.

```bash
git clone https://github.com/janszafranski/just-a-collection-of-apps.git
cd just-a-collection-of-apps
apps/webcreator/install.sh
```

Each app also checks this repository for a newer version of itself — **Help ▸
Check for Updates…** — and each has an `uninstall.sh` beside its installer.

## Layout

```
just-a-collection-of-apps/
├── apps/
│   └── webcreator/          the app, its installer, its data
└── docs/                    the site at janszafranski.github.io
```
