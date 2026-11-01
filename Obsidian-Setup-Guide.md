# Setting Up an Obsidian Vault for the 3D Horrendogram

How to build your own governance network in Obsidian and turn it into a 3D
horrendogram. No programming needed.

---

## The idea in one minute

You describe your network as a set of short notes. There are three kinds:

| Note kind | What it is | Becomes in the 3D view |
|---|---|---|
| **Actor** | An organisation: a ministry, agency, council, sector | A **circle** on its layer's ring |
| **Instrument** | A law, directive, plan, strategy, convention | A **square** on its layer's ring |
| **Interlinkage** | A relationship between two actors/instruments | A **line** between them |

Each actor and instrument says which **level** it belongs to (e.g. `eu`,
`national`). Every distinct level becomes one ring in the stack.

---

## Quick start

1. **Get the starter vault.** Download [`starter-vault.zip`](starter-vault.zip) and
   unzip it. It already has the right folders, three templates, and a few
   example notes.
2. **Open it in Obsidian.** *Open folder as vault* → choose the `starter-vault`
   folder. (Rename the folder to anything you like.)
3. **Delete the example notes** once you've looked at them, or keep them as a
   reference while you work.
4. **Add your own notes** using the templates. See
   [Using the templates in Obsidian](#using-the-templates-in-obsidian) for
   step-by-step instructions for each kind of note.
5. **Zip the vault folder** and upload it to the app under **Obsidian ZIP**, then
   click **Generate Visualization**.

---

## Folder structure

Your vault needs these three folders:

```
My Vault/
├── 1 Node - Actors/          ← one note per actor
├── 2 Node - Instruments/     ← one note per instrument
├── 10 Interlinkages/         ← one note per relationship
└── Templates/                ← optional; ignored by the app
```

The app recognises folders by the words **`Actors`**, **`Instruments`** and
**`Interlinkages`** in their names (upper or lower case doesn't matter). The
numbers in front are only there to sort the folders in Obsidian, so
`Actors`, `1 Node - Actors` and `Governance actors` all work.

> ⚠️ Those three words are how the app decides what a note is, so don't use
> them anywhere else in a folder or file name. A note called
> `Non-state actors.md` placed in `10 Interlinkages` would be read as an actor
> as well. Other folders (like `Templates`, or images) are ignored.

---

## Writing an actor or instrument note

**The file name is the node's name.** `European Commission.md` appears in the
3D view as *European Commission*. Choose the exact name you want shown, because
interlinkages refer to it.

```markdown
---
type: actor
level: eu
tags:
  - governance
---

## Description

The EU's executive body; it proposes EU legislation and monitors how member
states implement it. More at [the Commission's website](https://commission.europa.eu).
```

| Field | Required? | What to write |
|---|---|---|
| `type` | Recommended | `actor` or `instrument` (`legislation` also works and shows as a square). If left out, notes in the Actors folder count as actors and notes in the Instruments folder as instruments. Any other word (e.g. `pressure`, `measure`) shows as a **diamond** ("unknown type"). |
| `level` | **Yes** | The layer name, e.g. `global`, `eu`, `regional`, `national`, `sub-national`. You can invent your own levels. A note without a level lands on a layer called `unknown`. |
| `tags` | Optional | Topics used by the **Tag Filter**, e.g. `nutrients`, `water`. Leave empty if you don't need them. |
| `## Description` | Recommended | Shown in the details panel when you hover or click the node. |

---

## Writing an interlinkage note

The file name can be anything; `Source - Target.md` keeps things tidy.

```markdown
---
type: interlinkage
from: "[[European Commission]]"
to: "[[Water Framework Directive]]"
tags:
  - governance
---

## Description

The Commission proposed the directive and monitors its implementation in
member states.
```

| Field | Required? | What to write |
|---|---|---|
| `from` | **Yes** | A link to the source note: `"[[Exact Note Name]]"`, in quotes |
| `to` | **Yes** | A link to the target note, same format |
| `tags` | Optional | Topics for the Tag Filter |
| `## Description` | Recommended | Shown when you hover or click the line |

An interlinkage missing `from` or `to` is skipped. Each interlinkage connects
**exactly one** source to **one** target. To connect one actor to three laws,
write three interlinkage notes.

The direction matters for how you describe it, but the line itself has no arrow.

---

## The rules that matter most

These cause almost all "why does this look wrong?" moments:

1. **Links must match file names exactly.** `[[Ministry of Environment]]` will
   not find `Ministry of the Environment.md`. A link to a name with no matching
   note puts that node on the `unknown` layer as a diamond.
   *Tip:* type `[[` in Obsidian and pick the note from the suggestions instead
   of typing the name by hand.
2. **One link per field.** `from: "[[A]]"` works; `from: "[[A]], [[B]]"` does
   not. Aliases and headings are fine, though: `"[[Water Act|the Act]]"` and
   `"[[Water Act#Section 2]]"` both point to *Water Act*.
3. **Prefer quotes** around `"[[...]]"`. Obsidian adds them for you when you
   use its Properties editor, and the app also accepts a single unquoted link.
   If a properties block can't be read at all (e.g. a stray colon or bad
   indentation), that note is skipped.
4. **The `---` properties block must be the very first thing in the note**, with
   nothing (not even a blank line) above it.
5. **Use the heading `## Description` exactly.** The description runs until
   the next heading, so anything under a later heading (e.g.
   `## Related interlinkages`, `### Notes`) is not shown. Put everything you
   want displayed directly under `## Description`.
6. **One note per name.** Don't have an actor and an instrument with the same
   file name.
7. **Write levels consistently.** `EU` and `eu` are the same layer (case is
   ignored), but `sub-national` and `subnational` are two different layers.

Accented names (`Åland`, `Ministère`, `Umweltbundesamt`) are fine.

### In the description you can use

- **Links:** `[label](https://example.org)` or a bare `https://...` address.
  Both become clickable in the details panel.
- **Wiki links** like `[[Water Act]]` show as plain text.
- Keep it to plain sentences. Formatting such as bold, lists or tables shows as
  raw characters.

---

## Using the templates in Obsidian

The starter vault comes with three templates in its `Templates` folder, one for
each kind of note:

| Template | Use it for | Create the note in |
|---|---|---|
| **Actor template** | Organisations: ministries, agencies, councils, sectors | `1 Node - Actors` |
| **Instrument template** | Laws, directives, plans, strategies, conventions | `2 Node - Instruments` |
| **Interlinkage template** | A relationship between two existing notes | `10 Interlinkages` |

Obsidian's **Templates** core plugin is already switched on in the starter
vault and pointed at this folder. If you're using your own vault, do the
one-time setup below first.

### One-time setup (only for your own existing vault)

1. Copy the `Templates` folder from the starter vault into your vault.
2. *Settings → Core plugins* → turn on **Templates**.
3. *Settings → Templates* → set **Template folder location** to `Templates`.
4. Make sure you have the three folders described under
   [Folder structure](#folder-structure).

**Optional shortcut:** *Settings → Hotkeys* → search for
**Templates: Insert template** → click **+** and press a key combination, e.g.
`Ctrl/Cmd + T`. The steps below then become one key press instead of the
command palette.

### Creating an actor note

1. In the file list on the left, **right-click `1 Node - Actors` → New note**.
   Obsidian creates `Untitled.md` inside that folder.
2. **Type the actor's name as the note title**, replacing *Untitled*, e.g.
   `Ministry of the Environment`. This title is the file name, which is the
   name shown in 3D and the name interlinkages must link to.
3. Click in the empty note, press **`Ctrl/Cmd + P`**, type `insert template`,
   choose **Templates: Insert template**, then pick **Actor template**.
4. Fill in the properties at the top:
   - `type` — leave as `actor`
   - `level` — change `national` to the actor's level, e.g. `eu`
   - `tags` — replace `governance` with your own topic tags, or remove them
5. Under **Description**, **delete the placeholder sentence** (*"Write 2–4
   sentences…"*) and write your own. Otherwise the placeholder is what appears
   in the 3D view.

### Creating an instrument note

Same as an actor, but in the instruments folder and with the instrument template:

1. **Right-click `2 Node - Instruments` → New note.**
2. **Type the instrument's name as the title**, e.g. `Water Framework Directive`.
3. **`Ctrl/Cmd + P` → Templates: Insert template → Instrument template.**
4. Set `level` and `tags`. Leave `type` as `instrument`, or use `legislation`;
   both show as a square.
5. Replace the placeholder description with your own.

### Creating an interlinkage note

Create the two notes you want to connect **first**. An interlinkage only points
to notes that already exist.

1. **Right-click `10 Interlinkages` → New note.**
2. **Title it `Source - Target`**, e.g.
   `European Commission - Water Framework Directive`. The title isn't shown in
   3D, but this pattern makes notes easy to find later.
3. **`Ctrl/Cmd + P` → Templates: Insert template → Interlinkage template.**
4. Set `from`: click its value, delete `[[SOURCE NODE NAME]]`, type `[[` and
   start typing the source note's name. **Pick it from the suggestion list**
   instead of typing it out, so the spelling matches the file name exactly.
5. Set `to` the same way, for the target note.
6. Set `tags`, and replace the placeholder description with what the
   relationship means in practice.

To link one note to several others, repeat these steps once per connection.
Each interlinkage note holds exactly one `from` and one `to`.

### If the template doesn't look right

- **Properties appear as a table, not as text between `---` lines.** That's
  normal: it's Obsidian's Properties view of the same data. Click a value to
  edit it. To see the raw text instead, use *Settings → Editor → Properties in
  document → Source*.
- **Templates: Insert template isn't in the command palette.** The Templates
  core plugin is off; see [One-time setup](#one-time-setup-only-for-your-own-existing-vault).
- **"No templates found" or an empty list.** *Settings → Templates → Template
  folder location* must be exactly `Templates`.
- **The template went into the wrong note**, or something was already in the
  note. Undo with `Ctrl/Cmd + Z`, or delete the note and start again. Templates
  are easiest to insert into an empty note.
- **The note is in the wrong folder.** Drag it onto the right folder in the
  file list. Obsidian keeps links to it working.
- **Never edit the files in `Templates` to write a real note.** They're the
  blank forms you copy from. The app ignores that folder, so anything written
  there won't appear in 3D.

Notes don't need anything beyond what's in the templates. Extra properties,
headings, images and Dataview blocks are ignored by the app, so you can keep
working notes in the same vault.

---

## Zipping and uploading

**macOS:** right-click the vault folder → **Compress "…"**.
**Windows:** right-click the vault folder → **Send to → Compressed (zipped) folder**.

Zip the **whole vault folder**, not the individual folders inside it. The
hidden `.obsidian` folder and macOS's extra files are ignored, so you don't need
to remove them.

Then in the app: **Setup** tab → data source **Obsidian ZIP** → choose the file
→ **Generate Visualization**.

---

## What you'll see

- **Layers** are stacked alphabetically at first. Rearrange them on the
  **Filters** tab (▲/▼, then **Apply Order**). A typical order from top to
  bottom is `global`, `eu`, `regional`, `national`, `sub-national`.
- **Notes with no interlinkages** still appear, standing alone on their layer.
  This is a handy way to spot things you haven't connected yet.
- **Tags** from all notes appear as chips in the **Tag Filter**.

---

## Checklist before uploading

- [ ] Every actor/instrument has a `level`
- [ ] Every interlinkage has both `from` and `to`, one link each
- [ ] Every `[[link]]` matches a note's file name exactly
- [ ] Descriptions sit directly under `## Description`
- [ ] Level names are spelled the same way everywhere
- [ ] You zipped the whole vault folder

## Troubleshooting

| What you see | Likely cause | Fix |
|---|---|---|
| A layer called **unknown** | A note has no `level`, or a link doesn't match any file name | Add the level, or correct the link spelling |
| A **diamond** node | The same as above, or `type` is something other than actor/instrument/legislation | Correct the link or the `type` |
| Two rings that should be one | Level spelled two ways (`sub-national` vs `subnational`) | Use one spelling everywhere |
| A node with **no description** | Missing or misspelled `## Description` heading, or text placed under a different heading | Put the text directly under `## Description` |
| A relationship is **missing** | The interlinkage lacks `from` or `to`, or is outside the Interlinkages folder | Add both fields and check the folder |
| The same organisation appears **twice** | Two notes with slightly different names (e.g. `HELCOM` and `Helcom`) | Merge them into one note and update the links |
| A node shows the **wrong type or level** | An actor and an instrument share the same file name; only one of them is used | Give each note a unique name |
| Upload fails | The ZIP doesn't contain folders named with Actors / Instruments / Interlinkages | Check the folder names and zip the whole vault |
