"""Independent reader for workbench exports (verifier t_ebb2173c).

Deliberately does not import the viewer, common.js/ts or sca2_workbench.
Reads the .bin through the manifest offsets, which is the whole contract.
"""
import json
import struct
import os

DT = {
    "float32": ("f", 4),
    "float64": ("d", 8),
    "uint16": ("H", 2),
    "uint8": ("B", 1),
    "int32": ("i", 4),
}


class Export:
    def __init__(self, root):
        self.root = root
        self.index = json.load(open(os.path.join(root, "index.json")))

    def manifest(self, rel):
        return json.load(open(os.path.join(self.root, rel)))

    def read(self, man, name):
        """Return a nested list for array `name` of manifest `man`."""
        spec = man["arrays"][name]
        dt, size = DT[spec["dtype"]]
        off = spec["offset"]
        nbytes = spec["nbytes"]
        shape = spec["shape"]
        n = 1
        for s in shape:
            n *= s
        path = os.path.join(self.root, man["bin"])
        with open(path, "rb") as f:
            f.seek(off)
            raw = f.read(nbytes)
        assert len(raw) == nbytes, (path, off, nbytes, len(raw))
        flat = list(struct.unpack("<%d%s" % (n, dt), raw))
        assert len(flat) == n, (name, len(flat), n)
        return flat, shape

    def nested(self, man, name):
        flat, shape = self.read(man, name)
        if len(shape) == 1:
            return flat
        if len(shape) == 2:
            r, c = shape
            return [flat[i * c:(i + 1) * c] for i in range(r)]
        if len(shape) == 3:
            r, c, d = shape
            out = []
            for i in range(r):
                out.append([flat[(i * c + j) * d:(i * c + j + 1) * d] for j in range(c)])
            return out
        if len(shape) == 4:
            r, c, d, e = shape
            out = []
            for i in range(r):
                oi = []
                for j in range(c):
                    oj = []
                    for k in range(d):
                        base = ((i * c + j) * d + k) * e
                        oj.append(flat[base:base + e])
                    oi.append(oj)
                out.append(oi)
            return out
        raise ValueError(shape)

    def scalar(self, man, key):
        return man[key]
