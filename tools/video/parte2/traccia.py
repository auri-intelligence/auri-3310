"""Tracks the third-party logos in the clips (CSRT) and saves the boxes to blur in out/clip/<name>.json."""
import json
import os
import sys

import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
CLIP = os.path.join(HERE, 'out', 'clip')

# clip: [(x, y, w, h) on the first frame, at 1080x1920]
LOGHI = {
    'cover': [(625, 530, 130, 46)],
    'batteria': [(636, 618, 176, 124)],
}


def track(name):
    files = sorted(os.listdir(os.path.join(CLIP, name)))
    frames = [cv2.imread(os.path.join(CLIP, name, f)) for f in files]
    out = []
    for box in LOGHI[name]:
        tr = cv2.TrackerCSRT_create()
        tr.init(frames[0], box)
        boxes = [list(box)]
        for f in frames[1:]:
            ok, b = tr.update(f)
            boxes.append([int(v) for v in b] if ok else boxes[-1])
        out.append(boxes)
    json.dump(out, open(os.path.join(CLIP, name + '.json'), 'w'))
    sheet = []
    for i in range(0, len(frames), 4):
        f = frames[i].copy()
        for boxes in out:
            x, y, w, h = boxes[i]
            cv2.rectangle(f, (x, y), (x + w, y + h), (0, 0, 255), 6)
        sheet.append(cv2.resize(f[400:1200], (270, 200)))
    cv2.imwrite(os.path.join(HERE, 'out', 'prova', 'traccia_%s.png' % name), cv2.hconcat(sheet))


if __name__ == '__main__':
    for n in sys.argv[1:] or LOGHI:
        track(n)
