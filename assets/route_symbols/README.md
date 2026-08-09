# Route Symbol Assets

This directory stores vendored local PNG assets used by the image route-symbol backend.

## Policy

- Runtime reads only local files from this directory.
- Do not add runtime/startup downloads for symbol assets.
- Keep `ATTRIBUTION.md` updated when asset sources change.

## Import from `louh/mta-subway-bullets`

1. Download or clone `https://github.com/louh/mta-subway-bullets` manually on your machine.
2. Run the reference utility:

```powershell
python scripts/vendor_route_symbols.py --source-dir "C:\path\to\mta-subway-bullets" --clean
```

3. Commit generated `*.png` files in this directory.

`scripts/vendor_route_symbols.py` is not part of the deployed sign or an installed
CLI. It is retained solely to reproduce these checked-in assets if they need an
upstream refresh.

## Expected output

- Runtime-sized PNGs (default `10x10`) keyed by symbol name, for example:
  - `1.png`, `A.png`, `F.png`, `G.png`
  - `5D.png`, `6D.png`, `7D.png`
  - `SF.png`, `FD.png`, `S.png`, `SIR.png`
