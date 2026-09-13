# Framework API — QBCore / Qbox / ESX / ox

Query: `assetdb.py framework <name>` · Audit: `assetdb.py framework --check`
Build: `python scripts/build_framework.py --resources <server resources>`

## Why a separate layer

`lint_lua.py` verifies only **GTA natives**. But most bugs in a QBCore/ox resource are not in a
native, they are **in a framework call** — and none of them throws an error:

| bug | symptom |
|---|---|
| a non-existent event is triggered | the trigger goes nowhere, no log |
| a non-existent export is called | `nil value` **only when that line runs** — maybe once a month |
| `lib.showTextUi` (lowercase i) | no module, nil, silent |

## ⛔ The authority is the installed server, NOT upstream GitHub

The index is built **from the resources installed on the server**, not from the
`github.com/qbcore-framework` or `overextended` master. Reason: if an export was added upstream but
does not exist in your `qb-core`, calling it "valid" misleads. The `version` field from
`fxmanifest` is also written on every row.

Sample measurement (one QBCore server): **173 resources, 12,713 rows** —
2,569 event definitions · 1,002 exports · 501 commands · 321 callbacks · 115 ox_lib modules.

## Ecosystem — what replaces what

| framework | core | status |
|---|---|---|
| **QBCore** | `qb-core` | `exports['qb-core']:GetCoreObject()` |
| **Qbox** | `qbx_core` | QBCore fork; rewritten for code quality/security/performance, integrated with the ox resources |
| **ESX** | `es_extended` | separate ecosystem; its own events such as `esx:playerLoaded` |
| **ox_core** | `ox_core` | Overextended's own core |

**Qbox has no native `GetCoreObject`** — a bridge layer accepts the QBCore-style call for
compatibility. The Qbox docs say: most QBCore scripts run unchanged, except resources that touch a
database table directly, reach into undocumented `qb-core` internals or use it in invalid ways.

So the right pattern is not to pin one core but a **bridge**:

```lua
local core = exports['qb-core'] and exports['qb-core']:GetCoreObject()
          or exports.qbx_core and exports.qbx_core:GetCoreObject()
```

## Calls to a resource that is not installed — the strongest signal

Section **A** of the `framework --check` output. Measured: **345 calls / 58 resources** go to a
resource that is not installed on the server — `ox_inventory` 57, `qbx_core` 44,
`es_extended` 27. All of them fail silently at run time.

## ox_lib — two measured pitfalls

**1. Do not derive the module list from the `imports/` folder.** `imports/` gives 59 folders, but the
real API surface is **115**; `lib.notify` is defined under `resource/interface/client/notify.lua`.
The first version, which looked only at `imports/`, flagged **46.8%** of 2,216 `lib.*` calls as
"non-existent module" — `lib.notify` alone is used 380 times. After the fix the false positives
fell to **0.8%**.

**2. The docs list does not show the installed version.** The `overextended.dev` module list and the
file system are not the same. The file system is the authority.

## Dynamic export loop — searching for the literal name is not enough

`ox_target` exposes its exports like this:

```lua
for index, value in pairs(api) do exports(index, value) end
```

So **30+ real exports** such as `addBoxZone`, `addLocalEntity`, `removeZone` never appear in quotes
in the resource; they are only defined as `function api.X(`. An audit that does not recognise this
pattern counts them as "undefined export". Once it recognised it, typo candidates fell from
**69 → 29** calls.

## Why this audit is a WARNING, not an ERROR

Most of the remaining 29 candidates are **exports of resources written in JS/C#** —
`screenshot-basic:requestScreenshotUpload`, `oxmysql:execute`. They are invisible to a Lua scan.
Likewise `chat:addMessage` (79 uses) comes from FXServer's built-in `chat` resource and has no
folder in the server's `resources/` tree.

A linter that complains about everything stops being used, and then **you miss the real bugs too**.
So section A is a strong signal, B/C/D are warnings.

## ⛔ No rows does not mean no resource

In the first version the "installed resource" set was derived from the rows produced. A resource
that defines no export/event produces zero rows and **looks "not installed"** — this happened.
Fix: a separate `kind=resource` row is written for every scanned resource. The installed set is
read from there.

## Queries

```bash
assetdb.py framework GetCoreObject              # who calls it, where
assetdb.py framework qb-core --defs             # what qb-core PROVIDES
assetdb.py framework --kind lib_module          # the 115 ox_lib modules
assetdb.py framework --kind command             # the 501 registered commands
assetdb.py framework --check                    # A/B/C/D cross-check
```

## Sources

`docs.fivem.net/natives` · `docs.qbcore.org` · `docs.qbox.re` ·
`docs.esx-framework.org` · `overextended.dev/docs/ox_lib` ·
`github.com/{overextended,qbcore-framework,qbox-project,esx-framework}`

Note: the JetBrains page on `docs.qbcore.org` is sponsor information, not API.
