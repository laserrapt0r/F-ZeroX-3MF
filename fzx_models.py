#!/usr/bin/env python3
"""
F-ZeroX-3MF  -  F-Zero X (N64, Europa/PAL) -> 3D-druckbare Fahrzeugmodelle
==========================================================================

Liest die Fahrzeuggeometrie (hoechste Detailstufe) und die Decal-Texturen direkt
aus deiner eigenen ROM und erzeugt pro Fahrzeug:

  <nr>_<name>.stl              geschlossener, wasserdichter Volumenkoerper
                               (Original-Polygone, glatte Flaechen)
  <nr>_<name>_farbig.3mf       dasselbe Modell, Flaechen entlang der Farbgrenzen
                               der Texturen aufgeteilt; Farben als Filament-
                               Bemalung (OrcaSlicer, Anycubic Slicer Next,
                               Bambu Studio)
  <nr>_<name>_farbig.obj/.mtl  dasselbe als OBJ mit Materialfarben
  --render: Renderbilder aus mehreren Perspektiven + Gesamtuebersicht

Benoetigt die EUROPAEISCHE ROM (PAL), .z64 (.v64/.n64 werden automatisch
umgewandelt). Das Skript prueft die MD5-Summe der .z64-Daten:
  ee79a8fe287b5dcaea584439363342fc

Nutzung:
  python3 fzx_models.py "F-Zero X (Europe).z64" -o ausgabe
  python3 fzx_models.py ROM -o ausgabe --render
  python3 fzx_models.py ROM -o ausgabe -m blue_falcon -m golden_fox
  python3 fzx_models.py ROM --list
  python3 fzx_models.py --help

Abhaengigkeiten:  pip install numpy trimesh manifold3d triangle pillow

Das Skript enthaelt KEINE Spieldaten (keine Geometrie, keine Texturen, keine
Farben). Es enthaelt nur Adressen und Indizes, die beschreiben, wo die Daten in
der ROM liegen und wie die Display-Listen sie verknuepfen. Diese Angaben sind
aus dem oeffentlichen, unter CC0 stehenden Decompilation-Projekt
https://github.com/inspectredc/fzerox abgeleitet.

Lizenz: MIT (siehe LICENSE). F-Zero ist eine Marke von Nintendo; dieses Projekt
steht in keiner Verbindung zu Nintendo.
"""
import argparse, base64, hashlib, json, os, struct, sys, uuid, zipfile, zlib
import numpy as np

PAL_MD5 = 'ee79a8fe287b5dcaea584439363342fc'
RECIPES_B64 = (
    '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')

# ---------------------------------------------------------------- ROM access
def load_rom(path):
    d = open(path, 'rb').read()
    if d[:4] == b'\x37\x80\x40\x12':            # .v64 (byte-swapped)
        a = bytearray(d); a[0::2], a[1::2] = d[1::2], d[0::2]; d = bytes(a)
    elif d[:4] == b'\x40\x12\x37\x80':          # .n64 (little endian)
        d = np.frombuffer(d, '<u4').astype('>u4').tobytes()
    md5 = hashlib.md5(d).hexdigest()
    if md5 != PAL_MD5:
        sys.exit(f'Falsche ROM: MD5 {md5}\n'
                 f'Benoetigt wird F-Zero X (Europe, PAL) mit MD5 {PAL_MD5} (Format .z64).\n'
                 'Die US- und die japanische Version werden nicht unterstuetzt.')
    print(f'ROM OK: F-Zero X (Europe), MD5 {md5}')
    return d


def decode_tex(rom, off, fmt, w, h):
    img = np.zeros((h, w, 4), np.float64)
    if fmt == 'RGBA16':
        raw = np.frombuffer(rom[off:off + w * h * 2], '>u2').reshape(h, w).astype(np.int64)
        img[..., 0] = ((raw >> 11) & 31) / 31; img[..., 1] = ((raw >> 6) & 31) / 31
        img[..., 2] = ((raw >> 1) & 31) / 31; img[..., 3] = raw & 1
    elif fmt in ('I4', 'IA4'):
        raw = np.frombuffer(rom[off:off + w * h // 2], np.uint8).astype(np.int64)
        nib = np.empty(w * h, np.int64); nib[0::2] = raw >> 4; nib[1::2] = raw & 15
        nib = nib.reshape(h, w)
        if fmt == 'I4':
            img[..., :] = (nib / 15)[..., None]
        else:
            img[..., :3] = ((nib >> 1) / 7)[..., None]; img[..., 3] = nib & 1
    elif fmt in ('I8', 'IA8'):
        raw = np.frombuffer(rom[off:off + w * h], np.uint8).reshape(h, w).astype(np.int64)
        if fmt == 'I8':
            img[..., :] = (raw / 255)[..., None]
        else:
            img[..., :3] = ((raw >> 4) / 15)[..., None]; img[..., 3] = (raw & 15) / 15
    else:
        raise ValueError(fmt)
    return img


# ---------------------------------------------------------------- model + colours
def scale2x(img):
    """Scale2x/EPX pixel-art upscaler: doubles resolution, turns staircases into clean diagonals."""
    h, w = img.shape[:2]
    P = np.pad(img, ((1, 1), (1, 1), (0, 0)), mode='edge')
    E = P[1:-1, 1:-1]; B = P[:-2, 1:-1]; D = P[1:-1, :-2]; F = P[1:-1, 2:]; H = P[2:, 1:-1]
    eq = lambda a, b: np.all(a == b, axis=-1)[..., None]
    cond = ~eq(B, H) & ~eq(D, F)
    E0 = np.where(cond & eq(D, B), D, E); E1 = np.where(cond & eq(B, F), F, E)
    E2 = np.where(cond & eq(D, H), D, E); E3 = np.where(cond & eq(H, F), F, E)
    out = np.empty((2 * h, 2 * w, img.shape[2]), img.dtype)
    out[0::2, 0::2] = E0; out[0::2, 1::2] = E1; out[1::2, 0::2] = E2; out[1::2, 1::2] = E3
    return out


class Model:
    """Geometry (game units), per-corner UVs (texels) and N64 colour combiner."""

    def __init__(self, rom, rec, skin=0):
        self.rec = rec
        self.body = np.array(rec['skins'][skin], float) / 255
        self.tex = {int(t): (decode_tex(rom, v[0], v[1], v[2], v[3]), v[4], v[5]) for t, v in rec['tiles'].items()}
        self.up = 1
        self.tex_up = self.tex
        vbuf = [None] * 64
        verts, faces, mats, fmat = [], [], [], []
        for op in rec['ops']:
            if op[0] == 'V':
                _, off, n, v0 = op
                for k in range(n):
                    verts.append(struct.unpack('>hhhHhh', rom[off + 16 * k: off + 16 * k + 12]))
                    vbuf[v0 + k] = len(verts) - 1
            elif op[0] == 'M':
                mats.append(op[1:])
            else:
                faces.append([vbuf[op[1]], vbuf[op[2]], vbuf[op[3]]]); fmat.append(len(mats) - 1)
        v = np.array(verts, float)
        self.cpos = v[:, :3]                 # corner positions (game units)
        self.cuv = v[:, 4:6] / 32.0          # s10.5 -> texels
        self.faces = np.array(faces)         # indices into corner arrays
        self.fmat = np.array(fmat)
        self.mats = mats

    # texel fetch with N64 clamp / mirror / wrap
    @staticmethod
    def _wrap(c, mode, size):
        if 'C' in mode:
            return np.clip(c, 0, size - 1)
        if 'M' in mode:
            m = np.mod(c, 2 * size)
            return np.where(m >= size, 2 * size - 1 - m, m)
        return np.mod(c, size)

    def sample(self, tile, uv, bilinear=True):
        if tile not in self.tex:      # tile 0: reflection map loaded at runtime -> mid value
            return np.full((len(uv), 4), 0.5)
        img, cms, cmt = self.tex[tile]
        h, w = img.shape[:2]
        if not bilinear:
            x = self._wrap(np.floor(uv[:, 0]).astype(int), cms, w)
            y = self._wrap(np.floor(uv[:, 1]).astype(int), cmt, h)
            return img[y, x]
        if self.up > 1:      # pixel-art upscaled texture, nearest sampling
            img, cms, cmt = self.tex_up[tile]
            h, w = img.shape[:2]
            x = self._wrap(np.floor(uv[:, 0] * self.up).astype(int), cms, w)
            y = self._wrap(np.floor(uv[:, 1] * self.up).astype(int), cmt, h)
            return img[y, x]
        fx, fy = uv[:, 0] - 0.5, uv[:, 1] - 0.5
        x0, y0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
        ax, ay = (fx - x0)[:, None], (fy - y0)[:, None]
        X0, X1 = self._wrap(x0, cms, w), self._wrap(x0 + 1, cms, w)
        Y0, Y1 = self._wrap(y0, cmt, h), self._wrap(y0 + 1, cmt, h)
        return ((img[Y0, X0] * (1 - ax) + img[Y0, X1] * ax) * (1 - ay) +
                (img[Y1, X0] * (1 - ax) + img[Y1, X1] * ax) * ay)

    def color(self, mi, uv, bilinear=True):
        prim, env, comb, tile = self.mats[mi]
        n = len(uv)
        tex = self.sample(tile, uv, bilinear) if tile >= 0 else np.ones((n, 4))
        P = np.array(prim, float) / 255
        E = np.array(env, float) / 255 if env is not None else self.body
        src = {'TEXEL0': tex[:, :3], 'TEXEL0_ALPHA': np.repeat(tex[:, 3:4], 3, 1),
               'PRIMITIVE': np.tile(P, (n, 1)), 'ENVIRONMENT': np.tile(E, (n, 1)),
               '0': np.zeros((n, 3)), '1': np.ones((n, 3)), 'SHADE': np.ones((n, 3))}
        a, b, c, d = comb
        return np.clip((src[a] - src[b]) * src[c] + src[d], 0, 1)


def srgb2lab(c):
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], 1)


def build_palette(cols, wts, merge_de, max_colors):
    """Greedy area-weighted merging in CIELab; dominant clusters keep their colour."""
    lab = srgb2lab(cols)
    q = np.round(cols * 255 / 3).astype(int)
    uq, inv = np.unique(q, axis=0, return_inverse=True); inv = inv.ravel()
    area = np.bincount(inv, wts)
    L = np.stack([np.bincount(inv, wts * lab[:, k]) for k in range(3)], 1) / area[:, None]
    R = np.stack([np.bincount(inv, wts * cols[:, k]) for k in range(3)], 1) / area[:, None]
    act = list(range(len(uq))); tot = wts.sum()
    while len(act) > 1:
        A = np.array(act)
        D = np.linalg.norm(L[A][:, None] - L[A][None], axis=2); np.fill_diagonal(D, np.inf)
        i, j = np.unravel_index(np.argmin(D), D.shape)
        if D[i, j] > merge_de:
            small = [k for k in range(len(A)) if area[A[k]] < 0.002 * tot]
            if small:      # negligible blends/specks -> into their nearest colour
                i = min(small, key=lambda k: area[A[k]]); j = int(np.argmin(D[i]))
            elif len(A) <= max_colors:
                break
            # else: too many colours -> merge the two most similar ones (i, j)
        a, b = A[i], A[j]
        if area[a] < area[b]:
            a, b = b, a
        area[a] += area[b]; act.remove(b)
    A = np.array(sorted(act, key=lambda k: -area[k]))
    return np.clip(R[A], 0, 1), L[A]


# ---------------------------------------------------------------- geometry helpers
def tri_area(P):
    return np.linalg.norm(np.cross(P[..., 1, :] - P[..., 0, :], P[..., 2, :] - P[..., 0, :]), axis=-1) / 2


def clip_segment_to_tri(p, q, T, eps=1e-9):
    """Clip 2D segment p->q to triangle T (3x2, ccw). Returns (t0,t1) or None."""
    t0, t1 = 0.0, 1.0
    d = q - p
    for k in range(3):
        a, b = T[k], T[(k + 1) % 3]
        n = np.array([-(b - a)[1], (b - a)[0]])          # inward normal for ccw
        num = n @ (p - a); den = n @ d
        if abs(den) < 1e-15:
            if num < -eps:
                return None
            continue
        t = -num / den
        if den > 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1 - 1e-12:
            return None
    return t0, t1


class Colorizer:
    """Splits every original triangle along colour-region borders of its texture.
    Texels are first mapped to palette labels; the label map is then upscaled with
    Scale2x (res = 2, 4, 8 ...) so that pixel staircases become clean diagonals."""

    def __init__(self, model, palette_lab, res):
        self.m = model; self.pl = palette_lab
        k = max(0, int(round(np.log2(max(res, 1)))))
        self.res = 2 ** k
        self.maps = {}
        for mi, mat in enumerate(model.mats):
            tile = mat[3]
            if tile < 0 or tile not in model.tex:
                continue
            img, cms, cmt = model.tex[tile]
            h, w = img.shape[:2]
            yy, xx = np.mgrid[0:h, 0:w]
            uv = np.stack([xx.ravel() + 0.5, yy.ravel() + 0.5], 1).astype(float)
            lab = self._nearest(model.color(mi, uv, bilinear=False)).reshape(h, w, 1)
            for _ in range(k):
                lab = scale2x(lab)
            self.maps[mi] = (lab[..., 0], cms, cmt)

    def _nearest(self, c):
        return np.argmin(np.linalg.norm(srgb2lab(c)[:, None] - self.pl[None], axis=2), 1)

    def label(self, mi, uv):
        if mi not in self.maps:
            return self._nearest(self.m.color(mi, uv, bilinear=False))
        L, cms, cmt = self.maps[mi]
        h, w = L.shape
        x = Model._wrap(np.floor(uv[:, 0] * self.res).astype(int), cms, w)
        y = Model._wrap(np.floor(uv[:, 1] * self.res).astype(int), cmt, h)
        return L[y, x]

    def cell_label(self, mi, ix, iy):
        f = self.res
        uv = np.stack([(ix + 0.5) / f, (iy + 0.5) / f], 1)
        return self.label(mi, uv)

    def segments(self, fi):
        """Colour-border segments of face fi in barycentric coords: list of (b0, b1)."""
        m = self.m
        mi = m.fmat[fi]; tile = m.mats[mi][3]
        if tile < 0 or tile not in m.tex:
            return []
        UV = m.cuv[m.faces[fi]]
        A = (UV[1, 0] - UV[0, 0]) * (UV[2, 1] - UV[0, 1]) - (UV[2, 0] - UV[0, 0]) * (UV[1, 1] - UV[0, 1])
        if abs(A) < 1e-9:
            return []
        f = self.res
        T = UV * f
        if A < 0:
            Tc = T[[0, 2, 1]]
        else:
            Tc = T
        lo = np.floor(T.min(0)).astype(int) - 1; hi = np.ceil(T.max(0)).astype(int) + 1
        nx, ny = hi[0] - lo[0], hi[1] - lo[1]
        if nx * ny > 2_000_000:
            return []
        ix, iy = np.meshgrid(np.arange(lo[0], hi[0]), np.arange(lo[1], hi[1]), indexing='ij')
        lab = self.cell_label(mi, ix.ravel(), iy.ravel()).reshape(nx, ny)
        segs = []
        # vertical borders x = lo0 + i (between cell i-1 and i)
        vi, vj = np.nonzero(lab[1:, :] != lab[:-1, :])
        for i, j in zip(vi, vj):
            x = lo[0] + i + 1; y = lo[1] + j
            segs.append((np.array([x, y], float), np.array([x, y + 1], float)))
        hi_, hj = np.nonzero(lab[:, 1:] != lab[:, :-1])
        for i, j in zip(hi_, hj):
            x = lo[0] + i; y = lo[1] + j + 1
            segs.append((np.array([x, y], float), np.array([x + 1, y], float)))
        # barycentric conversion
        Minv = np.linalg.inv(np.array([[T[1, 0] - T[0, 0], T[2, 0] - T[0, 0]],
                                       [T[1, 1] - T[0, 1], T[2, 1] - T[0, 1]]]))
        def bary(p):
            l12 = Minv @ (p - T[0])
            return np.array([1 - l12.sum(), l12[0], l12[1]])
        out = []
        for p, q in segs:
            c = clip_segment_to_tri(p, q, Tc)
            if c is None:
                continue
            t0, t1 = c
            if t1 - t0 < 1e-7:
                continue
            b0 = bary(p + (q - p) * t0); b1 = bary(p + (q - p) * t1)
            # discard segments lying on a triangle edge
            if any(abs(b0[k]) < 1e-7 and abs(b1[k]) < 1e-7 for k in range(3)):
                continue
            out.append((np.clip(b0, 0, 1), np.clip(b1, 0, 1)))
        return out

    def label_at_bary(self, fi, B):
        UV = self.m.cuv[self.m.faces[fi]]
        return self.label(self.m.fmat[fi], B @ UV)


def classify_and_cap(m, key, wid, WF, good, log=print):
    """Split the welded triangle soup into
       - plates: double-sided (or leftover open) zero-thickness triangles -> become prisms
       - solids: closed shells; components with small holes get the holes capped.
    Shells that only touch along an edge (non-manifold edges) are kept apart."""
    fidx = np.nonzero(good)[0]
    fkey = {}
    for fi in fidx:
        fkey.setdefault(tuple(sorted(WF[fi])), []).append(fi)
    twin = {}
    for k, fs in fkey.items():
        if len(fs) == 2:
            twin[fs[0]] = fs[1]; twin[fs[1]] = fs[0]
    rest = [fi for fi in fidx if fi not in twin]
    parent = {f: f for f in rest}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    emap = {}
    for fi in rest:
        for k in range(3):
            a, b = WF[fi][k], WF[fi][(k + 1) % 3]
            emap.setdefault((min(a, b), max(a, b)), []).append((fi, a))
    for e, lst in emap.items():
        # connect only across proper manifold edges (exactly two uses, opposite direction)
        if len(lst) == 2 and lst[0][1] != lst[1][1]:
            parent[find(lst[0][0])] = find(lst[1][0])
    comps = {}
    for fi in rest:
        comps.setdefault(find(fi), []).append(fi)
    m._wid = wid.copy()
    solids, plates = [], []
    new_faces, new_mats = [], []
    for fs in comps.values():
        de = {}
        for fi in fs:
            for k in range(3):
                a, b = WF[fi][k], WF[fi][(k + 1) % 3]
                de[(a, b)] = de.get((a, b), 0) + 1
        open_e = [(a, b) for (a, b), v in de.items() for _ in range(v - de.get((b, a), 0)) if v > de.get((b, a), 0)]
        if not open_e:
            solids.append(list(fs)); continue
        if len(fs) < 4:
            plates += [(fi, None) for fi in fs]; continue
        # cap holes: boundary loops, reversed orientation, fan triangulation
        nxt = {}
        ok = True
        for a, b in open_e:
            if b in nxt:
                ok = False; break
            nxt[b] = a                      # cap edge b -> a
        caps = []
        if ok:
            seen = set()
            for start in list(nxt):
                if start in seen:
                    continue
                loop = [start]; seen.add(start); cur = nxt[start]
                while cur != start:
                    if cur in seen or cur not in nxt:
                        ok = False; break
                    loop.append(cur); seen.add(cur); cur = nxt[cur]
                if not ok:
                    break
                # fan from the apex that gives the best-shaped (non-degenerate) triangles
                best, best_a = None, -1
                Kp = key.astype(float)
                for r0 in range(len(loop)):
                    lp = loop[r0:] + loop[:r0]
                    tr = [[lp[0], lp[i], lp[i + 1]] for i in range(1, len(lp) - 1)]
                    amin = min(tri_area(Kp[np.array(t)][None])[0] for t in tr)
                    if amin > best_a:
                        best, best_a = tr, amin
                caps += best     # may be degenerate (T-junction 'holes' of zero area) - fine for the boolean
        if not ok or len(caps) > 0.5 * len(fs):
            plates += [(fi, None) for fi in fs]; continue
        # colour of a cap: colour of the face owning the first boundary edge
        own = {}
        for fi in fs:
            for k in range(3):
                own[(WF[fi][k], WF[fi][(k + 1) % 3])] = fi
        cap_ids = []
        for c in caps:
            src = own.get((c[1], c[0])) or own.get((c[2], c[1])) or own.get((c[0], c[2])) or fs[0]
            col = m.color(m.fmat[src], m.cuv[m.faces[src]].mean(0, keepdims=True), bilinear=False)[0]
            base = len(m.cpos) + 3 * len(new_faces)
            new_faces.append((c, col))
            cap_ids.append(len(m.faces) + len(new_faces) - 1)
        solids.append(list(fs) + cap_ids)
        log(f'      {len(caps)} Loch-Dreiecke geschlossen')
    for a, b in twin.items():
        if a < b:
            plates.append((a, b))
    # append cap faces to the model (own corners, constant-colour material)
    if new_faces:
        cpos, cuv, faces, fmat = [m.cpos], [m.cuv], [m.faces], [m.fmat]
        widl = [m._wid]
        n0 = len(m.cpos)
        for j, (c, col) in enumerate(new_faces):
            cpos.append(key[c].astype(float)); cuv.append(np.zeros((3, 2)))
            faces.append(np.array([[n0 + 3 * j, n0 + 3 * j + 1, n0 + 3 * j + 2]]))
            widl.append(np.array(c))
            m.mats.append([[int(round(x * 255)) for x in col], [0, 0, 0], ['0', '0', '0', 'PRIMITIVE'], -1])
            fmat.append(np.array([len(m.mats) - 1]))
        m.cpos = np.vstack(cpos); m.cuv = np.vstack(cuv); m.faces = np.vstack(faces)
        m.fmat = np.concatenate(fmat); m._wid = np.concatenate(widl)
    return solids, plates


# ---------------------------------------------------------------- solid construction
def build(model, mm_per_unit, thick, res, merge_de, max_colors, colored=True, log=print):
    import trimesh, triangle, manifold3d as mf, copy
    m = copy.deepcopy(model)
    P_c = m.cpos[:, [2, 0, 1]] * mm_per_unit           # game (x,y,z) -> print (z,x,y)
    key, wid = np.unique(m.cpos.astype(np.int64), axis=0, return_inverse=True)
    wid = wid.ravel()
    WP = key[:, [2, 0, 1]].astype(float) * mm_per_unit  # welded positions (mm)
    WF = wid[m.faces]                                   # welded faces
    nF = len(WF)
    good = tri_area(WP[WF]) > 1e-9
    solids, plates = classify_and_cap(m, key, wid, WF, good, log)
    wid = m._wid
    WF = wid[m.faces]
    good = np.concatenate([good, np.ones(len(WF) - len(good), bool)])
    nF = len(WF)
    # --- palette from area-weighted surface samples
    rng = np.random.default_rng(1)
    ar = tri_area(WP[WF]) * good
    cnt = np.maximum((ar / ar.sum() * 150000).astype(int), 8) * good
    cols, wts = [], []
    for fi in np.nonzero(good)[0]:
        r = rng.random((cnt[fi], 2)); s = r.sum(1) > 1; r[s] = 1 - r[s]
        B = np.c_[1 - r.sum(1), r]
        uv = B @ m.cuv[m.faces[fi]]
        cols.append(m.color(m.fmat[fi], uv, bilinear=False)); wts.append(np.full(cnt[fi], ar[fi] / cnt[fi]))
    palette, pal_lab = build_palette(np.vstack(cols), np.concatenate(wts), merge_de, max_colors)
    cz = Colorizer(m, pal_lab, res)

    # --- colour borders -> points on edges (shared between neighbouring faces)
    segs = {fi: (cz.segments(fi) if colored else []) for fi in np.nonzero(good)[0]}
    eparams = {}
    for fi, sl in segs.items():
        for b0, b1 in sl:
            for b in (b0, b1):
                for k in range(3):
                    if b[k] < 1e-7:   # on edge opposite corner k
                        i, j = (k + 1) % 3, (k + 2) % 3
                        wi, wj = WF[fi][i], WF[fi][j]
                        t = b[j] / (b[i] + b[j])
                        if wi > wj:
                            wi, wj, t = wj, wi, 1 - t
                        if 1e-6 < t < 1 - 1e-6:
                            eparams.setdefault((wi, wj), []).append(t)
    for e in eparams:
        ts = np.sort(np.array(eparams[e]))
        keep = [ts[0]]
        for t in ts[1:]:
            if t - keep[-1] > 1e-7:
                keep.append(t)
        eparams[e] = np.array(keep)

    def epos(wi, wj, t):
        return WP[wi] + t * (WP[wj] - WP[wi])

    def edge_points(a, b):
        """points strictly inside welded edge a->b as (key, pos, bary-param from a)"""
        lo_, hi_ = min(a, b), max(a, b)
        ts = eparams.get((lo_, hi_), np.zeros(0))
        out = [(('e', lo_, hi_, int(round(t * 1e9))), epos(lo_, hi_, t), (t if a == lo_ else 1 - t)) for t in ts]
        return sorted(out, key=lambda x: x[2])

    def split_face(fi):
        """CDT of face fi with its colour borders -> list of ((key,key,key), (pos,pos,pos), label)"""
        w = WF[fi]; Pw = WP[w]
        e1 = Pw[1] - Pw[0]; e1 /= np.linalg.norm(e1)
        n = np.cross(Pw[1] - Pw[0], Pw[2] - Pw[0]); n /= np.linalg.norm(n)
        e2 = np.cross(n, e1)
        to2 = lambda p: np.array([(p - Pw[0]) @ e1, (p - Pw[0]) @ e2])
        keys, pts2, pos3, bary = [], [], [], []
        def add(kk, p3, b):
            keys.append(kk); pos3.append(p3); pts2.append(to2(p3)); bary.append(b); return len(keys) - 1
        ring = []
        for k in range(3):
            a, b = w[k], w[(k + 1) % 3]
            B = np.zeros(3); B[k] = 1
            ring.append(add(('v', a), WP[a], B))
            for kk, p3, t in edge_points(a, b):
                B = np.zeros(3); B[k] = 1 - t; B[(k + 1) % 3] = t
                ring.append(add(kk, p3, B))
        segl = [(ring[i], ring[(i + 1) % len(ring)]) for i in range(len(ring))]
        lookup = {kk: i for i, kk in enumerate(keys)}
        interior = {}
        def pt_index(b):
            for k in range(3):
                if b[k] < 1e-7:
                    i, j = (k + 1) % 3, (k + 2) % 3
                    wi, wj = w[i], w[j]
                    t = b[j] / (b[i] + b[j])
                    if wi > wj:
                        wi, wj, t = wj, wi, 1 - t
                    if t <= 1e-6:
                        return lookup[('v', wi)]
                    if t >= 1 - 1e-6:
                        return lookup[('v', wj)]
                    ts = eparams[(wi, wj)]
                    tt = ts[np.argmin(np.abs(ts - t))]
                    return lookup[('e', wi, wj, int(round(tt * 1e9)))]
            kk = ('f', fi, tuple(np.round(b, 9)))
            if kk not in interior:
                interior[kk] = add(kk, b @ Pw, b)
            return interior[kk]
        for b0, b1 in segs.get(fi, []):
            i0, i1 = pt_index(b0), pt_index(b1)
            if i0 != i1:
                segl.append((i0, i1))
        if tri_area(Pw[None])[0] < 1e-8 or not np.all(np.isfinite(np.array(pts2))):
            # degenerate (zero-area) cap triangle: fan over its boundary ring, no colour split
            out = [[ring[0], ring[i], ring[i + 1]] for i in range(1, len(ring) - 1)]
            labs = cz.label_at_bary(fi, np.array([[1 / 3, 1 / 3, 1 / 3]])) if colored else [0]
            return [((keys[t[0]], keys[t[1]], keys[t[2]]), (pos3[t[0]], pos3[t[1]], pos3[t[2]]), int(labs[0])) for t in out]
        if len(keys) == 3:
            tris = [[0, 1, 2]]
            V2 = np.array(pts2)
        else:
            res_ = triangle.triangulate({'vertices': np.array(pts2), 'segments': np.array(segl)}, 'pQ')
            V2 = res_['vertices']; tris = res_['triangles']
            # Steiner points (should only appear in the interior)
            for vi in range(len(keys), len(V2)):
                p2 = V2[vi]
                p3 = Pw[0] + p2[0] * e1 + p2[1] * e2
                Mb = np.linalg.lstsq(np.c_[Pw[1] - Pw[0], Pw[2] - Pw[0]], p3 - Pw[0], rcond=None)[0]
                add(('s', fi, vi), p3, np.array([1 - Mb.sum(), Mb[0], Mb[1]]))
        out = []
        for t in tris:
            a2, b2, c2 = (V2[i] for i in t)
            if (b2 - a2)[0] * (c2 - a2)[1] - (b2 - a2)[1] * (c2 - a2)[0] < 0:
                t = [t[0], t[2], t[1]]
            out.append(t)
        B = np.array(bary)
        cen = np.array([B[t].mean(0) for t in out])
        labs = cz.label_at_bary(fi, cen) if colored else np.zeros(len(out), int)
        return [((keys[t[0]], keys[t[1]], keys[t[2]]), (pos3[t[0]], pos3[t[1]], pos3[t[2]]), int(l))
                for t, l in zip(out, labs)]

    pieces = []   # (V, F, labels) closed meshes
    # solids
    for fs in solids:
        kidx, V, F, L = {}, [], [], []
        for fi in fs:
            for ks, ps, l in split_face(fi):
                tri = []
                for kk, p in zip(ks, ps):
                    if kk not in kidx:
                        kidx[kk] = len(V); V.append(p)
                    tri.append(kidx[kk])
                F.append(tri); L.append(l)
        V, F, L = np.array(V), np.array(F), np.array(L)
        tm = trimesh.Trimesh(V, F, process=False)
        if tm.volume < 0:
            F = F[:, ::-1]
        pieces.append((V, F, L))
    # plates -> prisms of thickness `thick`
    for fa, fb in plates:
        w = WF[fa]; Pw = WP[w]
        n = np.cross(Pw[1] - Pw[0], Pw[2] - Pw[0]); n /= np.linalg.norm(n)
        o = n * thick / 2
        V, F, L = [], [], []
        def addv(p):
            V.append(p); return len(V) - 1
        top = split_face(fa)
        bot = split_face(fb) if fb is not None else [((k[0], k[2], k[1]), (p[0], p[2], p[1]), l) for k, p, l in top]
        for ks, ps, l in top:
            F.append([addv(p + o) for p in ps]); L.append(l)
        for ks, ps, l in bot:
            F.append([addv(p - o) for p in ps]); L.append(l)
        for k in range(3):
            a, b = w[k], w[(k + 1) % 3]
            chain = [WP[a]] + [p for _, p, _ in edge_points(a, b)] + [WP[b]]
            Bm = np.full(3, 0.02); Bm[k] = 0.49; Bm[(k + 1) % 3] = 0.49
            lab = int(cz.label_at_bary(fa, Bm[None])[0]) if colored else 0
            for p, q in zip(chain[:-1], chain[1:]):
                i0, i1, i2, i3 = addv(p + o), addv(q + o), addv(q - o), addv(p - o)
                F += [[i0, i2, i1], [i0, i3, i2]]; L += [lab, lab]
        V, F, L = np.array(V), np.array(F), np.array(L)
        # merge identical positions, fix orientation
        uq, inv = np.unique(np.round(V, 9), axis=0, return_inverse=True)
        V = uq; F = inv.ravel()[F]
        keepf = (F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])
        F, L = F[keepf], L[keepf]
        tm = trimesh.Trimesh(V, F, process=False)
        trimesh.repair.fix_winding(tm)
        F2 = np.array(tm.faces)
        # fix_winding keeps face order; recompute labels mapping by order
        if tm.volume < 0:
            F2 = F2[:, ::-1]
        # grow 1 % to avoid exactly coincident faces with neighbours
        c = V.mean(0); V = c + (V - c) * 1.01
        pieces.append((V, F2, L))

    def union(pcs):
        ms = []
        for V, F, L in pcs:
            mg = mf.Mesh64(vert_properties=np.ascontiguousarray(V, np.float64),
                           tri_verts=np.ascontiguousarray(F, np.uint64),
                           face_id=np.ascontiguousarray(L, np.uint64))
            mm = mf.Manifold(mg)
            if mm.status() != mf.Error.NoError:
                log('  warn: piece not manifold:', mm.status())
                continue
            ms.append(mm)
        man = mf.Manifold.batch_boolean(ms, mf.OpType.Add)
        parts = sorted([c for c in man.decompose() if abs(c.volume()) > 0.5], key=lambda c: -c.volume())
        if len(parts) > 1:
            # parts floating free in the game (spoilers, fins) get a small strut to the main body
            mo = parts[0].to_mesh64()
            MV = np.asarray(mo.vert_properties)[:, :3]; MF = np.asarray(mo.tri_verts).astype(np.int64)
            ML = np.asarray(mo.face_id).astype(np.int64)
            main_tm = trimesh.Trimesh(MV, MF, process=False)
            extra = []
            for c in parts[1:]:
                po = c.to_mesh64()
                PV = np.asarray(po.vert_properties)[:, :3]
                cp, dist, tri = trimesh.proximity.closest_point(main_tm, PV)
                k = int(np.argmin(dist))
                a, b = PV[k], cp[k]
                d = (b - a) / max(np.linalg.norm(b - a), 1e-9)
                a2, b2 = a - d * 0.8, b + d * 0.8
                rr = 0.8
                cap = mf.Manifold.batch_hull([mf.Manifold.sphere(rr, 24).translate(tuple(a2)),
                                              mf.Manifold.sphere(rr, 24).translate(tuple(b2))])
                cm = cap.to_mesh64()
                lab = int(ML[tri[k]])
                cap = mf.Manifold(mf.Mesh64(vert_properties=np.array(np.asarray(cm.vert_properties)[:, :3], dtype=np.float64, order='C'),
                                            tri_verts=np.array(np.asarray(cm.tri_verts), dtype=np.uint64, order='C').reshape(-1, 3),
                                            face_id=np.full(len(np.asarray(cm.tri_verts)), lab, np.uint64)))
                extra.append(cap)
                log(f'      Steg zu losem Teil ({c.volume():.0f} mm3, Abstand {dist[k]:.2f} mm)')
            grown = []
            for c in parts[1:]:
                bb = np.asarray(c.bounding_box()).reshape(2, 3)
                ctr = bb.mean(0); rad = max(np.linalg.norm(bb[1] - bb[0]) / 2, 1e-3)
                sc = 1 + 0.25 / rad
                grown.append(c.translate(tuple(-ctr)).scale((sc, sc, sc)).translate(tuple(ctr)))
            man = mf.Manifold.batch_boolean(parts[:1] + grown + extra, mf.OpType.Add)
            parts = [c for c in man.decompose() if abs(c.volume()) > 0.5]
            man = mf.Manifold.batch_boolean(parts, mf.OpType.Add) if len(parts) > 1 else parts[0]
        else:
            man = parts[0]
        out = man.to_mesh64()
        V = np.asarray(out.vert_properties)[:, :3].copy()
        F = np.asarray(out.tri_verts).astype(np.int64)
        L = np.asarray(out.face_id).astype(np.int64)
        return V, F, L, len(parts)

    V, F, L, nb = union(pieces)
    # snap to float32 (file precision). Vertices are merged by position only where that keeps
    # every edge shared by exactly two triangles; touching-but-separate shells keep their own
    # vertex copies (valid topology for 3MF/OBJ).
    V32 = V.astype(np.float32).astype(np.float64)
    uq, inv = np.unique(V32, axis=0, return_inverse=True)
    F2 = inv.ravel()[F]
    keep = (F2[:, 0] != F2[:, 1]) & (F2[:, 1] != F2[:, 2]) & (F2[:, 0] != F2[:, 2])
    e = np.sort(np.concatenate([F2[keep][:, [0, 1]], F2[keep][:, [1, 2]], F2[keep][:, [2, 0]]]), 1)
    _, ec = np.unique(e, axis=0, return_counts=True)
    if (ec == 2).all():
        F, L, V = F2[keep], L[keep], uq
        used = np.unique(F); rm = -np.ones(len(V), np.int64); rm[used] = np.arange(len(used))
        V = V[used]; F = rm[F]
    else:
        V = V32
        log(f'      Hinweis: {int((ec != 2).sum())} Beruehrungskanten bleiben als getrennte Kanten erhalten')
    shift = np.r_[-(V[:, :2].min(0) + V[:, :2].max(0)) / 2, -V[:, 2].min()]
    V = V + shift
    info = dict(n_solids=len(solids), n_plates=len(plates), bodies=nb)
    return V, F, L, palette, info


# ---------------------------------------------------------------- export
COLOR_NAMES = {
    'schwarz': (20, 20, 20), 'dunkelgrau': (75, 75, 75), 'grau': (128, 128, 128), 'hellgrau': (190, 190, 190),
    'weiss': (245, 245, 245), 'rot': (220, 20, 20), 'dunkelrot': (130, 15, 30), 'orange': (240, 120, 20),
    'gelb': (250, 220, 30), 'gold': (205, 165, 50), 'oliv': (100, 100, 20), 'gruen': (20, 160, 60),
    'dunkelgruen': (15, 70, 30), 'hellgruen': (140, 220, 40), 'petrol': (0, 110, 110), 'tuerkis': (60, 200, 210),
    'hellblau': (120, 170, 220), 'blau': (20, 40, 230), 'marine': (15, 20, 70), 'lila': (120, 60, 190),
    'violett': (160, 90, 230), 'magenta': (220, 40, 160), 'pink': (240, 90, 140), 'braun': (110, 70, 30),
    'beige': (200, 180, 120), 'stahlblau': (70, 80, 150),
}


def color_name(rgb):
    lab = srgb2lab(np.array(list(COLOR_NAMES.values())) / 255)
    return list(COLOR_NAMES)[int(np.argmin(np.linalg.norm(lab - srgb2lab(np.array([rgb]))[0], axis=1)))]


def write_stl(path, V, F):
    T = V[F].astype('<f4')
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    rec = np.zeros(len(F), dtype=[('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')])
    rec['n'] = n; rec['v'] = T
    with open(path, 'wb') as fo:
        fo.write(b'F-Zero X machine - binary STL (mm)'.ljust(80, b' '))
        fo.write(np.uint32(len(F)).tobytes()); fo.write(rec.tobytes())


def write_obj(path, V, F, L, palette, names):
    base = os.path.splitext(os.path.basename(path))[0]
    with open(os.path.splitext(path)[0] + '.mtl', 'w') as fo:
        for k, c in enumerate(palette):
            fo.write(f'newmtl {names[k]}\nKd {c[0]:.4f} {c[1]:.4f} {c[2]:.4f}\nKa 0 0 0\nKs 0 0 0\nd 1\nillum 1\n\n')
    with open(path, 'w') as fo:
        fo.write(f'mtllib {base}.mtl\n')
        fo.write(''.join('v %.9g %.9g %.9g\n' % tuple(v) for v in V.astype(np.float32)))
        for k in range(len(palette)):
            sel = F[L == k]
            if len(sel):
                fo.write(f'usemtl {names[k]}\n')
                fo.write(''.join(f'f {a + 1} {b + 1} {c + 1}\n' for a, b, c in sel))



def paint_code(state):          # TriangleSelector serialisation of an unsplit triangle
    if state <= 0: return None
    if state < 3: return '%X' % (state << 2)
    return '%XC' % (state - 3)

def write_orca_3mf(path, V, F, L, palette_hex, title, project_cfg=None):
    obj_model = ['<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
                 'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
                 'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
                 'xmlns:slic3rpe="http://schemas.slic3r.org/3mf/2017/06" '
                 'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">\n'
                 ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n <resources>\n'
                 f'  <object id="1" p:UUID="{uuid.uuid4()}" type="model">\n   <mesh>\n    <vertices>\n']
    obj_model.append(''.join(f'     <vertex x="{x:.7g}" y="{y:.7g}" z="{z:.7g}"/>\n' for x, y, z in V))
    obj_model.append('    </vertices>\n    <triangles>\n')
    codes = [paint_code(int(l) + 1) for l in L]
    obj_model.append(''.join(f'     <triangle v1="{a}" v2="{b}" v3="{c}" paint_color="{p}" slic3rpe:mmu_segmentation="{p}"/>\n' for (a, b, c), p in zip(F, codes)))
    obj_model.append('    </triangles>\n   </mesh>\n  </object>\n </resources>\n <build/>\n</model>\n')
    cx, cy = 128.0, 128.0
    main = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
            'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
            'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
            'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">\n'
            ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
            f' <metadata name="Title">{title}</metadata>\n <resources>\n'
            f'  <object id="2" p:UUID="{uuid.uuid4()}" type="model">\n   <components>\n'
            f'    <component p:path="/3D/Objects/object_1.model" objectid="1" p:UUID="{uuid.uuid4()}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n'
            '   </components>\n  </object>\n </resources>\n'
            f' <build p:UUID="{uuid.uuid4()}">\n  <item objectid="2" p:UUID="{uuid.uuid4()}" transform="1 0 0 0 1 0 0 0 1 {cx} {cy} 0" printable="1"/>\n </build>\n</model>\n')
    rels3d = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
              ' <Relationship Target="/3D/Objects/object_1.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n</Relationships>\n')
    settings = ('<?xml version="1.0" encoding="UTF-8"?>\n<config>\n  <object id="2">\n'
                f'    <metadata key="name" value="{title}"/>\n    <metadata key="extruder" value="1"/>\n'
                '    <part id="1" subtype="normal_part">\n'
                f'      <metadata key="name" value="{title}"/>\n'
                '      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n'
                '    </part>\n  </object>\n  <plate>\n    <metadata key="plater_id" value="1"/>\n'
                '    <metadata key="plater_name" value=""/>\n    <metadata key="locked" value="false"/>\n'
                '    <model_instance>\n      <metadata key="object_id" value="2"/>\n'
                '      <metadata key="instance_id" value="0"/>\n    </model_instance>\n  </plate>\n</config>\n')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n <Default Extension="png" ContentType="image/png"/>\n <Default Extension="gcode" ContentType="text/x.gcode"/>\n</Types>\n')
        z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n</Relationships>\n')
        z.writestr('3D/3dmodel.model', main)
        z.writestr('3D/_rels/3dmodel.model.rels', rels3d)
        z.writestr('3D/Objects/object_1.model', ''.join(obj_model))
        z.writestr('Metadata/model_settings.config', settings)
        if project_cfg is not None:
            z.writestr('Metadata/project_settings.config', json.dumps(project_cfg, indent=4))


# ---------------------------------------------------------------- software renderer (numpy only)
VIEWS = {
    'vorne_links':  (-35, 22),   # azimuth (deg, 0 = from the front/+X), elevation
    'hinten_rechts': (145, 25),
    'seite':        (90, 0),
    'oben':         (0, 89),
    'vorne':        (0, 8),
    'hinten':       (180, 8),
}


def _look(az, el, center, radius, fov):
    a, e = np.radians(az), np.radians(el)
    d = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])   # from center to eye
    dist = radius / np.sin(np.radians(fov) / 2) * 1.08
    eye = center + d * dist
    fwd = -d
    up = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.99 else np.array([-1.0, 0.0, 0.0])
    right = np.cross(fwd, up); right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    return eye, right, up, fwd


def render_view(V, F, C, az, el, width=2400, height=1600, ssaa=2, background=(244, 244, 242), fov=24.0):
    """Flat-shaded, anti-aliased z-buffer render. V (n,3) mm, F (m,3), C (m,3) colours 0..1.
    Returns a PIL image (RGBA, transparent background if background is None)."""
    from PIL import Image
    W, H = width * ssaa, height * ssaa
    center = (V.min(0) + V.max(0)) / 2
    radius = np.linalg.norm(V - center, axis=1).max()
    eye, right, up, fwd = _look(az, el, center, radius, fov)
    rel = V - eye
    z = rel @ fwd
    u = (rel @ right) / z; v = -(rel @ up) / z          # normalised image coords
    margin = 0.06
    f = min(W * (1 - 2 * margin) / (u.max() - u.min()), H * (1 - 2 * margin) / (v.max() - v.min()))
    sx = W / 2 + f * (u - (u.max() + u.min()) / 2)
    sy = H / 2 + f * (v - (v.max() + v.min()) / 2)
    T = np.stack([sx[F], sy[F]], -1)                 # (m,3,2)
    Z = z[F]
    area = ((T[:, 1, 0] - T[:, 0, 0]) * (T[:, 2, 1] - T[:, 0, 1]) - (T[:, 2, 0] - T[:, 0, 0]) * (T[:, 1, 1] - T[:, 0, 1]))
    vis = area < -1e-9                               # counter-clockwise in world -> clockwise on screen (y down)
    # shading (flat, two lights + ambient), done in linear light
    P3 = V[F]
    n = np.cross(P3[:, 1] - P3[:, 0], P3[:, 2] - P3[:, 0]); n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    l1 = -fwd * 0.35 + up * 0.75 - right * 0.65; l1 /= np.linalg.norm(l1)
    l2 = np.array([0.3, 0.6, 0.75]); l2 /= np.linalg.norm(l2)
    lin = np.asarray(C, float) ** 2.2
    shade = 0.14 + 0.72 * np.clip(n @ l1, 0, 1) + 0.22 * np.clip(n @ l2, 0, 1)
    col = np.clip(lin * shade[:, None], 0, 1) ** (1 / 2.2)
    zbuf = np.full(W * H, np.inf)
    fid = np.full(W * H, -1, np.int64)
    ids = np.nonzero(vis)[0]
    # scanline rasterisation, fully vectorised: rows -> spans -> pixels (no wasted work)
    def spans(ch):
        t = T[ch]; zz = Z[ch]
        y0 = np.ceil(t[:, :, 1].min(1) - 0.5).astype(np.int64); y1 = np.floor(t[:, :, 1].max(1) - 0.5).astype(np.int64)
        y0 = np.maximum(y0, 0); y1 = np.minimum(y1, H - 1)
        hgt = np.maximum(y1 - y0 + 1, 0)
        ti = np.repeat(np.arange(len(ch)), hgt)
        if not len(ti):
            return None
        row = y0[ti] + (np.arange(len(ti)) - np.repeat(np.cumsum(hgt) - hgt, hgt))
        yc = row + 0.5
        xl = np.full(len(ti), np.inf); xr = np.full(len(ti), -np.inf)
        for a_, b_ in ((0, 1), (1, 2), (2, 0)):
            ya, yb = t[ti, a_, 1], t[ti, b_, 1]; xa, xb = t[ti, a_, 0], t[ti, b_, 0]
            dy = yb - ya
            with np.errstate(divide='ignore', invalid='ignore'):
                tt = (yc - ya) / dy
            ok = (dy != 0) & (tt >= 0) & (tt <= 1)
            x = xa + tt * (xb - xa)
            xl = np.where(ok, np.minimum(xl, x), xl); xr = np.where(ok, np.maximum(xr, x), xr)
        c0 = np.maximum(np.ceil(xl - 0.5), 0); c1 = np.minimum(np.floor(xr - 0.5), W - 1)
        cnt = np.where(np.isfinite(c0) & np.isfinite(c1), np.maximum(c1 - c0 + 1, 0), 0).astype(np.int64)
        pr = np.repeat(np.arange(len(ti)), cnt)
        if not len(pr):
            return None
        px = c0[pr].astype(np.int64) + (np.arange(len(pr)) - np.repeat(np.cumsum(cnt) - cnt, cnt))
        py = row[pr]
        tri = ti[pr]
        # depth plane per triangle: z = A x + B y + C
        p0, p1_, p2_ = t[:, 0], t[:, 1], t[:, 2]
        M = np.stack([p1_ - p0, p2_ - p0], 2)          # (n,2,2) columns
        det = M[:, 0, 0] * M[:, 1, 1] - M[:, 0, 1] * M[:, 1, 0]
        det = np.where(np.abs(det) < 1e-12, 1e-12, det)
        dz1, dz2 = zz[:, 1] - zz[:, 0], zz[:, 2] - zz[:, 0]
        A = (dz1 * M[:, 1, 1] - dz2 * M[:, 1, 0]) / det
        B = (dz2 * M[:, 0, 0] - dz1 * M[:, 0, 1]) / det
        Cc = zz[:, 0] - A * p0[:, 0] - B * p0[:, 1]
        d = A[tri] * (px + 0.5) + B[tri] * (py + 0.5) + Cc[tri]
        return py * W + px, d, ch[tri]
    chunks = []
    approx = (np.ptp(T[ids][:, :, 0], 1) + 1) * (np.ptp(T[ids][:, :, 1], 1) + 1)
    cs = np.cumsum(approx); lim = 6e6
    starts = [0] + list(np.searchsorted(cs, np.arange(lim, cs[-1] if len(cs) else 0, lim)))
    bounds = sorted(set(starts + [len(ids)]))
    for p in (0, 1):
        for i0, i1 in zip(bounds[:-1], bounds[1:]):
            r = spans(ids[i0:i1])
            if r is None:
                continue
            idx, d, tri = r
            if p == 0:
                o = np.lexsort((d, idx)); idx, d = idx[o], d[o]
                first = np.ones(len(idx), bool); first[1:] = idx[1:] != idx[:-1]
                u = idx[first]; zbuf[u] = np.minimum(zbuf[u], d[first])
            else:
                win = d <= zbuf[idx] + 1e-9
                fid[idx[win]] = tri[win]
    img = np.zeros((W * H, 4))
    hit = fid >= 0
    img[hit, :3] = col[fid[hit]]
    img[hit, 3] = 1
    if background is not None:
        bg = np.array(background, float) / 255
        img[~hit, :3] = bg; img[~hit, 3] = 1
    im = Image.fromarray((img.reshape(H, W, 4) * 255).round().astype(np.uint8), 'RGBA')
    if ssaa > 1:
        im = im.resize((width, height), Image.LANCZOS)
    return im


def render_all_views(path_stem, V, F, C, views, size, title=None):
    from PIL import Image, ImageDraw
    w, h = size
    ims = []
    for name in views:
        az, el = VIEWS[name]
        im = render_view(V, F, C, az, el, w, h)
        im.convert('RGB').save(f'{path_stem}_render_{name}.png', optimize=True)
        ims.append(im)
    # contact sheet of all views
    cols = 3 if len(ims) > 4 else len(ims)
    rows = (len(ims) + cols - 1) // cols
    tw, th = w // 2, h // 2
    sheet = Image.new('RGB', (cols * tw, rows * th), (244, 244, 242))
    for i, im in enumerate(ims):
        sheet.paste(im.convert('RGB').resize((tw, th), Image.LANCZOS), ((i % cols) * tw, (i // cols) * th))
    if title:
        from PIL import ImageFont
        try:
            font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', max(18, th // 18))
        except OSError:
            font = ImageFont.load_default()
        ImageDraw.Draw(sheet).text((20, 14), title, fill=(40, 40, 40), font=font)
    sheet.save(f'{path_stem}_render_uebersicht.png', optimize=True)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description='F-Zero X (PAL) Fahrzeuge -> druckbare STL/OBJ/3MF')
    ap.add_argument('rom', nargs='?', help='Pfad zur europaeischen F-Zero-X-ROM (.z64/.v64/.n64)')
    ap.add_argument('-o', '--out', default='fzerox_modelle', help='Ausgabeordner (Standard: fzerox_modelle)')
    ap.add_argument('-m', '--machine', action='append', help='z.B. blue_falcon (mehrfach moeglich; Standard: alle)')
    ap.add_argument('--list', action='store_true', help='verfuegbare Fahrzeuge auflisten')
    ap.add_argument('--length', type=float, default=100.0, help='Laenge der Blue Falcon in mm (gemeinsamer Massstab, Standard 100)')
    ap.add_argument('--thick', type=float, default=1.2, help='Dicke fuer hauchduenne Flaechen (Finnen/Fluegel) in mm')
    ap.add_argument('--skin', type=int, default=0, choices=range(4), help='Lackierung 0-3 (0 = Standard)')
    ap.add_argument('--smooth', type=int, default=8, help='Kantenglaettung der Decals: 1 = pixelgenau wie N64-Textur, '
                    '2/4/8/16 = Pixel-Art-Hochskalierung (Scale2x) fuer saubere Diagonalen')
    ap.add_argument('--max-colors', type=int, default=16, help='Obergrenze fuer die Anzahl Farben (Standard: alle)')
    ap.add_argument('--merge', type=float, default=12.0, help='Farben mit Delta-E kleiner als dieser Wert zusammenfassen')
    ap.add_argument('--no-color', action='store_true', help='nur STL erzeugen')
    ap.add_argument('--render', action='store_true', help='hochaufgeloeste Renderbilder aus mehreren Perspektiven erzeugen')
    ap.add_argument('--views', default=','.join(VIEWS), help='Perspektiven, kommagetrennt: ' + ', '.join(VIEWS))
    ap.add_argument('--render-size', default='2400x1600', help='Bildgroesse BxH in Pixeln (Standard 2400x1600)')
    ap.add_argument('--map', default='', help='Farben zusammenlegen, z.B. "8=5,4=3" (Farbe 8 wird zu 5, 4 zu 3; '
                    'Nummern wie im normalen Lauf ausgegeben). Nur sinnvoll zusammen mit -m fuer ein Fahrzeug.')
    a = ap.parse_args()
    recipes = json.loads(zlib.decompress(base64.b64decode(RECIPES_B64)))
    if a.list:
        for i, r in enumerate(recipes):
            print(f'{i + 1:2d}  {r["slug"]:18s} {r["name"]}')
        return
    if not a.rom:
        ap.error('Pfad zur ROM fehlt')
    rom = load_rom(a.rom)
    os.makedirs(a.out, exist_ok=True)
    sel = [(i, r) for i, r in enumerate(recipes) if not a.machine or r['slug'] in a.machine or str(i + 1) in a.machine]
    if not sel:
        sys.exit('Keine passende Maschine gefunden (siehe --list).')
    mmpu = a.length / 560.0
    overview = []
    for i, r in sel:
        stem = f'{i + 1:02d}_{r["slug"]}'
        print(f'[{i + 1:2d}/30] {r["name"]} ...', flush=True)
        model = Model(rom, r, a.skin)
        V, F, _, _, info = build(model, mmpu, a.thick, a.smooth, a.merge, a.max_colors, colored=False)
        write_stl(os.path.join(a.out, stem + '.stl'), V, F)
        msg = f'      STL: {len(F)} Dreiecke, {info["bodies"]} Koerper, Groesse ' + ' x '.join(f'{x:.1f}' for x in V.max(0) - V.min(0)) + ' mm'
        print(msg)
        if not a.no_color:
            V, F, L, pal, info = build(model, mmpu, a.thick, a.smooth, a.merge, a.max_colors, colored=True)
            used = np.unique(L)
            remap = -np.ones(len(pal), int); remap[used] = np.arange(len(used))
            L = remap[L]; pal = pal[used]
            if a.map:
                mp = np.arange(len(pal))
                for item in a.map.split(','):
                    src, dst = (int(x) - 1 for x in item.split('='))
                    mp[mp == src] = dst
                L = mp[L]
                used = np.unique(L)
                remap = -np.ones(len(pal), int); remap[used] = np.arange(len(used))
                L = remap[L]; pal = pal[used]
            names = [f'{k + 1}_{color_name(c)}_{"%02X%02X%02X" % tuple(int(round(x * 255)) for x in c)}' for k, c in enumerate(pal)]
            write_obj(os.path.join(a.out, stem + '_farbig.obj'), V, F, L, pal, names)
            hexes = ['#%02X%02X%02X' % tuple(int(round(x * 255)) for x in c) for c in pal]
            write_orca_3mf(os.path.join(a.out, stem + '_farbig.3mf'), V, F, L, hexes, f'F-Zero X {r["name"]}')
            print(f'      farbig: {len(F)} Dreiecke, Farben: ' + ', '.join(names))
            CF = pal[L]
        else:
            CF = np.full((len(F), 3), 0.7); hexes = []
        if a.render:
            w, h = (int(x) for x in a.render_size.lower().split('x'))
            views = [v.strip() for v in a.views.split(',') if v.strip()]
            render_all_views(os.path.join(a.out, stem), V, F, CF, views, (w, h), r['name'])
            overview.append((i + 1, r['name'], os.path.join(a.out, f'{stem}_render_{views[0]}.png'), hexes))
            print(f'      Renderbilder: {len(views)} Perspektiven')

    if len(overview) > 1:
        make_overview(os.path.join(a.out, '00_uebersicht.png'), overview)
        print('Uebersicht:', os.path.join(a.out, '00_uebersicht.png'))


def make_overview(path, items, cols=5, tw=720, th=480):
    from PIL import Image, ImageDraw, ImageFont, ImageChops
    try:
        font = ImageFont.truetype('DejaVuSans-Bold.ttf', 26)
    except OSError:
        try:
            font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 26)
        except OSError:
            font = ImageFont.load_default()
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * tw, rows * (th + 70)), (244, 244, 242))
    d = ImageDraw.Draw(sheet)
    for n, (nr, name, png, hexes) in enumerate(items):
        im = Image.open(png).convert('RGB')
        bg = Image.new('RGB', im.size, im.getpixel((0, 0)))
        bb = ImageChops.difference(im, bg).getbbox() or (0, 0, im.width, im.height)
        im = im.crop(bb); im.thumbnail((tw - 30, th - 20), Image.LANCZOS)
        x, y = (n % cols) * tw, (n // cols) * (th + 70)
        sheet.paste(im, (x + (tw - im.width) // 2, y + 10 + (th - 20 - im.height) // 2))
        d.text((x + 18, y + th + 2), f'{nr:02d}  {name}', fill=(30, 30, 30), font=font)
        for k, hx in enumerate(hexes):
            d.rectangle((x + 18 + k * 30, y + th + 38, x + 42 + k * 30, y + th + 60), fill=hx, outline=(120, 120, 120))
    sheet.save(path, optimize=True)


if __name__ == '__main__':
    main()
