---
description: Look at what is currently on Peter's reMarkable tablet. The tablet casts its live screen to tab.danenberg.ai as a PNG; fetch it and read it. Use whenever he refers to something he has written, drawn, sketched or annotated — "take a look at my tablet", "I had a question written down", "see what I marked up".
---

# Look at the tablet

Peter's reMarkable casts its current page to `https://tab.danenberg.ai/f.png`
as a plain PNG. No auth, no API, no session — one GET returns whatever is on
the screen right now.

## Fetch it

```sh
curl -fsS https://tab.danenberg.ai/f.png -o /tmp/tablet.png && file /tmp/tablet.png
```

Then read `/tmp/tablet.png` with the image tool and describe what is on it.

Expect roughly 1620×2160, greyscale, handwriting in black with annotations
often in red. It is a *photograph of a page*, so read it the way you would
read someone's notebook over their shoulder: the layout carries meaning,
arrows point at things, circled text is emphasis, and marginalia are usually
the point.

## When it 404s, the tablet simply is not casting

This is the common failure and it is not an error worth debugging. The URL is
served only while a cast is running; between casts, `GET /f.png` returns 404
and the index page still links to it. Nothing is broken.

Say so plainly — "I can't see the tablet, it doesn't look like it's casting" —
and let him start it. Do not retry in a loop, and do not go looking for
another URL: `/f.png` is the whole interface.

`HEAD` returns 404 even when a frame *is* available, so `curl -I` cannot tell
the two cases apart. Use `GET`, as above.

## What he usually wants

Not a transcription. He has already read it — he wants you to have read it
too, so he can talk about it. Lead with the substance: what the note says,
what the annotation is objecting to, what the sketch is of. If there is a
question written on the page, answer it.
