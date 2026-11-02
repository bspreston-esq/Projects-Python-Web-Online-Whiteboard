# Online White Board

**Category:** Web

## Problem

Create an application which allows you to draw pictures, write notes and use various colors to flesh out ideas for projects. Optional: Add feature to invite friends to collaborate on a white board online.

## Solution

A stdlib HTTP server serves an HTML5 canvas front end and a small JSON API: GET/POST/DELETE `/api/strokes?room=<name>` stores polylines per room under a lock, and the page polls every two seconds so multiple browsers share a board. Colour and brush width are client-side controls.

## How to run

Requires Python 3.8+ and no third-party packages.

```bash
python3 main.py --port 8000     # then open http://127.0.0.1:8000/
python3 main.py --demo
```

## Example

```text
canvas page: True | bytes: 3107
post: {'ok': True, 'strokes': 1}
strokes stored: 1, points: 3
after clear: 0
```

## Attribution

The problem statement is from [karan/Projects](https://github.com/karan/Projects), a list of practical projects that anyone can solve in any programming language (MIT License, Copyright (c) 2013 Karan Goel). The Python solution in this repository was implemented by [bspreston-esq](https://github.com/bspreston-esq).

This repository is part of the [Projects-Python-All](https://github.com/bspreston-esq/Projects-Python-All) collection.
