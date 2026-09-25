# Forms Pro Fork — Frappe v16 Compatibility & General-Purpose Form Platform Plan

**File:** `plan.md`  
**Project:** Fork and extend `bwhtech/forms_pro`  
**Primary target:** Frappe Framework v16 / ERPNext v16  
**Product goal:** A polished, general-purpose website form builder for Frappe DocTypes, inspired by HubSpot Forms but native to Frappe  
**Frontend:** Vue 3 + TypeScript + Frappe UI + Tailwind + Vite  
**Backend:** Frappe v16 / Python 3.14+  
**Status:** Architecture and implementation plan  
**Prepared:** 2026-09-17

---

# 1. Executive Decision

We will **fork Forms Pro** and evolve it into a production-ready, general-purpose form platform for Frappe v16.

We will **not**:

- rebuild the application from scratch,
- rewrite the frontend in React,
- make Contact the center of the architecture,
- directly modify Frappe/ERPNext core,
- make published forms depend on live DocType metadata,
- allow public clients to choose arbitrary target DocTypes/fields,
- rely on upstream Forms Pro behavior that mutates linked DocTypes.

We **will** retain useful Forms Pro foundations:

- Vue 3 SPA,
- Frappe UI,
- drag-and-drop builder,
- form renderer,
- field components,
- Pinia stores,
- team management,
- public form routes,
- routing,
- conditional logic,
- responsive layout,
- existing test tooling.

The product architecture becomes:

```text
                        FORMS PRO FORK
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
     Form Builder       Success Builder      Design System
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
                         Draft Schema
                              │
                         Publish/Version
                              │
                    Immutable Form Version
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
       Standalone Runtime                 Embed Runtime
              │                               │
              └───────────────┬───────────────┘
                              │
                         Submission API
                              │
              Security + Validation Layer
                              │
                         Mapping Engine
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
      FP Form Submission               Target DocType
                                               │
                                      Any supported DocType
```

The most important sequence is:

```text
1. Make the fork genuinely Frappe v16 compatible
2. Stop destructive DocType synchronization
3. Introduce a generic mapping/submission engine
4. Add safe immutable publishing/versioning
5. Improve builder UX
6. Add success-page designer
7. Add external embed
8. Add CAPTCHA/security
9. Add analytics/tracking
10. UAT + migration + production hardening
```

---

# 2. Primary Product Vision

The fork should become a **general form layer above Frappe DocTypes**.

A user should be able to:

1. choose a target DocType,
2. select existing fields,
3. add form-only fields,
4. map form-only fields to target fields,
5. change labels/help/defaults without modifying the DocType,
6. build multi-column and multi-page layouts,
7. configure conditional logic,
8. add hidden/preset values,
9. upload files,
10. visually style the form,
11. design the post-submission success experience,
12. preview desktop/tablet/mobile,
13. publish an immutable version,
14. use a standalone URL,
15. embed it into an external website,
16. submit securely,
17. create/update a target Frappe document,
18. keep an independent submission audit record,
19. view form analytics,
20. archive a form without deleting history.

The target DocType could be:

```text
Lead
Contact
Customer
Supplier
Issue
Opportunity
Quotation
Job Applicant
Event
Project
Task
a custom DocType
or another supported DocType
```

The architecture must not contain business logic that assumes any one of these is the main use case.

---

# 3. Meaning of “Support Every DocType”

The architecture should support **any eligible Frappe DocType**, but not expose unsafe/system DocTypes blindly.

There are different DocType capabilities.

## 3.1 Normal Standard DocType

Example:

```text
Lead
Issue
Opportunity
Task
Project
```

Support:

```text
Create New
Update Existing
Upsert if matching rules are configured
Draft save when relevant
Field mapping
Attachments
Child-table mapping
```

---

## 3.2 Custom DocType

Fully supported through the same generic engine.

No special application code should be needed merely because:

```text
custom = 1
```

---

## 3.3 Child Table DocType

A child DocType should **not normally be a root public target**.

Instead:

```text
Parent DocType
  └── Table field
        └── Child DocType fields
```

Example:

```text
Quotation
  └── items
        └── Quotation Item
```

The form can render a repeating section and map rows into the parent Table field.

---

## 3.4 Single DocType

Single DocTypes do not behave like ordinary document collections.

Therefore:

```text
Create New -> not applicable
Update Existing -> possible through explicit adapter/configuration
```

Single DocTypes should be disabled as public targets by default.

They can be enabled only by System Manager through a capability policy.

---

## 3.5 Submittable DocType

Examples may use:

```text
docstatus
```

Default public behavior:

```text
Create Draft
```

Optional setting:

```text
After successful validation:
○ Save Draft
○ Submit Document
```

`Submit Document` must be explicitly enabled and subject to:

- form-level permission,
- server validation,
- DocType controller validation,
- required workflow/business rules.

Never automatically submit merely because a DocType is submittable.

---

## 3.6 Tree DocType

Potentially supported when required parent/tree fields are available.

The capability inspector should warn if a selected tree DocType requires fields that the form does not provide.

---

## 3.7 Virtual DocType

Disabled by default.

Can be enabled only when the virtual controller supports the required save/update behavior and passes compatibility tests.

---

## 3.8 System/Security-Sensitive DocTypes

Do not expose unsafe internal DocTypes as public form targets.

Examples that should be denied by policy unless explicitly developed for:

```text
User
Role
System Settings
DocType
Custom Field
Server Script
OAuth Client
API Key related records
Installed Applications
Email Account
```

“General DocType support” means the **engine is generic**, not that every internal administrative DocType is safe for anonymous creation.

---

# 4. Research-Based Current State of Forms Pro

Forms Pro already provides a useful foundation.

Current repository features include:

```text
Vue 3
TypeScript
Vite
Frappe UI
Tailwind
Pinia
Vue Draggable
Zod
Playwright
Vitest
Drag/drop builder
Real-time preview
DocType linking
Team management
Custom routes
Public submission page
Conditional logic
Save-incomplete capability
```

Forms Pro's own repository documentation describes it as a form builder linked to any Frappe DocType.

However, several current implementation decisions must be corrected before extending the product.

---

# 5. Critical Upstream Architecture Problem — DocType Mutation

Current `Form.on_update()` calls:

```python
self.set_doctype_fields()
```

The current method can change the linked DocType's:

```text
label
fieldtype
reqd
options
description
default
fieldname
```

and can add fields directly to the target DocType.

That is not appropriate for the required product.

A form must be a **presentation and mapping layer**, not a schema editor.

Required invariant:

> Saving or publishing a form must never silently alter the target DocType schema.

New design:

```text
Target DocType Field
        │
        │ metadata read
        ▼
    Form Field
        │
        ├── custom label
        ├── custom help text
        ├── required-on-form
        ├── hidden-on-form
        ├── form default
        ├── layout
        ├── conditions
        └── design properties

NO schema mutation
```

This should be protected by automated regression tests.

---

# 6. Second Upstream Architecture Problem — Target DocType Pollution

Current Forms Pro may add target fields such as:

```text
fp_linked_form
fp_submission_status
```

to target DocTypes.

For a general form system, this should not be required.

The target DocType should not need to know that Forms Pro exists.

Replace:

```text
Target document
  ├── fp_linked_form
  └── fp_submission_status
```

with:

```text
FP Form Submission
  ├── form
  ├── version
  ├── target_doctype
  ├── target_name
  ├── status
  └── response metadata
```

Benefits:

- no Custom Fields added to customer DocTypes,
- one document can have multiple form submissions,
- analytics becomes accurate,
- target schema remains clean,
- easier uninstall/migration,
- supports any target DocType,
- avoids collisions with business fields.

---

# 7. Highest Priority: Frappe v16 Compatibility Program

Frappe v16 compatibility is a **release gate**, not a side task.

No client feature should be considered production-ready until the fork passes the v16 compatibility matrix.

---

# 8. Frappe v16 Runtime Baseline

Official Frappe v16 migration guidance requires:

```text
Python 3.14+
Node.js 24+
```

The fork must standardize development, CI, staging and production around these versions.

Recommended branch contract:

```text
Python: >=3.14,<3.15
Node: >=24,<25
Frappe: >=16.0.0,<17.0.0
ERPNext: compatible version-16
```

---

# 9. Current Dependency Mismatches to Correct

Current Forms Pro declares:

```toml
requires-python = ">=3.14"
```

which is aligned.

But Ruff currently declares:

```toml
target-version = "py313"
```

Change to:

```toml
target-version = "py314"
```

Current Frappe dependency is broad:

```toml
frappe = ">=16.0.0-dev,<18.0.0"
```

For the production `version-16` branch use:

```toml
frappe = ">=16.0.0,<17.0.0"
```

Do not claim v17 compatibility until tested separately.

---

# 10. Node 24 Alignment

Current frontend uses modern dependencies, but the target runtime is Node 24.

Add:

```json
{
  "engines": {
    "node": ">=24 <25"
  }
}
```

The current project uses a Node 25 type package.

For strict compatibility, pin Node type definitions to the runtime generation:

```text
@types/node -> 24.x
```

This avoids TypeScript compiling against APIs that may exist in Node type definitions newer than the actual supported runtime.

---

# 11. Frappe v16 Compatibility Audit Matrix

Every item below needs:

```text
Code audit
Automated test where possible
Manual smoke test
Documented pass/fail
```

---

## 11.1 Python 3.14

Audit:

- deprecated syntax,
- dependencies that do not support 3.14,
- Faker constraints,
- dnspython,
- email-validator,
- test libraries,
- import behavior.

CI must run actual Python 3.14.

---

## 11.2 Node 24

Audit:

- Vite build,
- vue-tsc,
- Vitest,
- Playwright,
- PostCSS,
- Tailwind,
- vuedraggable,
- Frappe UI,
- Pinia,
- TypeScript.

Run:

```bash
node --version
yarn install --frozen-lockfile
yarn typecheck
yarn lint
yarn test:unit
yarn build
```

---

## 11.3 Frappe v16 Navigation

Frappe v16 introduces the newer app screen/persistent navigation architecture.

Forms Pro already uses:

```python
add_to_apps_screen
```

which should be retained and tested.

Validate:

```text
Apps screen icon
/forms route
Open in Desk behavior if needed
SPA direct refresh
Workspace/sidebar behavior
role visibility
mobile Desk navigation
```

If a curated Frappe Sidebar is added, use the v16-supported module sidebar structure.

Do not rely on old `workspace_sidebar` fixture patterns.

---

## 11.4 Permission Hook Semantics

Frappe v16 changed permission hook expectations.

Audit every:

```text
has_permission
permission_query_conditions
DocShare check
team permission check
```

Functions must return explicit booleans when required.

Forms Pro's app-screen permission function currently returns bool, which is good.

Test:

```text
Administrator
System Manager
Forms Pro Manager
Forms Pro User
non-Forms-Pro user
Guest
```

---

## 11.5 Query Builder / `get_list` / `get_all`

Frappe v16 moved more database APIs onto Query Builder.

Audit all queries involving:

```python
frappe.get_all
frappe.get_list
frappe.db.get_all
frappe.db.get_value
frappe.db.get_values
frappe.qb
```

Look for:

- unsupported filter structures,
- raw SQL assumptions,
- implicit join behavior,
- group/order clauses,
- child-table filters.

Create integration tests for all core list/query endpoints.

---

## 11.6 Default Sort Changed to `creation`

Frappe v16 defaults many APIs/list views to `creation` instead of `modified`.

Audit any Forms Pro logic that assumes:

```text
first result == most recently modified
```

Use explicit:

```python
order_by="modified desc"
```

when that is the actual intent.

UI lists should choose intentionally:

```text
Recently updated
Created recently
Alphabetical
Most submissions
```

Do not depend on implicit database ordering.

---

## 11.7 Single DocType Value Casting

Frappe v16 changed some `db.get_value` behavior for Single DocTypes to return native values.

Audit code such as:

```python
value == "1"
```

when v16 may return:

```python
value == 1
```

Prefer:

```python
frappe.utils.cint(value)
```

where boolean interpretation is intended.

---

## 11.8 State-Changing HTTP Methods

Frappe v16 tightened POST requirements for several state-changing APIs.

Our fork should adopt a stronger rule:

```text
Reads -> GET/RPC read endpoint
Writes -> POST only
```

All Forms Pro state-changing APIs should explicitly declare:

```python
@frappe.whitelist(methods=["POST"])
```

where appropriate.

Audit:

```text
create form
save form
publish
archive
team mutation
invite acceptance
submission
file upload
retry
duplicate
```

Avoid state mutation through redirect-driven GET requests.

---

## 11.9 Translation Changes

Frappe v16 removed older translation APIs/hooks.

Audit:

```text
get_translated_dict
frappe.get_lang_dict
frappe.translate.get_dict
doc.meta.__messages
```

Frontend form labels should rely on:

```text
published form label
configured translation strategy
```

rather than deprecated global metadata dictionaries.

---

## 11.10 Test Flag Changes

Audit:

```python
frappe.flags.in_test
```

Prefer:

```python
frappe.in_test
```

where v16 recommends it.

---

## 11.11 Website/Public Route Behavior

Test:

```text
/forms
/forms/edit-form/<id>
/forms/manage/<id>
/forms/p/<route>
refresh on each route
guest load
published/unpublished behavior
404 handling
production proxy
```

---

## 11.12 Asset Build

Verify production output:

```text
forms_pro/public/frontend
/assets/forms_pro/frontend/*
forms_pro/www/forms.html
```

Test cache-busted production builds.

No frontend should depend on Vite dev server in production.

---

## 11.13 Frappe UI Compatibility

Pin a tested `frappe-ui` range.

Do not automatically upgrade to latest during production deploy.

Create a compatibility file:

```text
docs/compatibility/frontend.md
```

Record:

```text
Frappe version
Frappe UI version
Vue version
Vite version
Node version
known issues
```

---

## 11.14 User Invitation / Team Hooks

Forms Pro hooks into:

```text
User
User Invitation
DocShare
team creation
```

These are sensitive to Frappe changes.

Audit:

- invitation acceptance,
- role changes,
- duplicate team creation,
- recursion,
- permissions,
- redirect behavior,
- POST/GET semantics.

Avoid manually invoking controller lifecycle methods such as `on_update()` unless required and proven safe.

---

## 11.15 Installation

Clean-site test:

```bash
bench get-app <fork> --branch version-16
bench --site test.local install-app forms_pro
bench build --app forms_pro
bench --site test.local migrate
```

Must pass without manual database changes.

---

## 11.16 Upgrade Test

Test upgrade from upstream baseline:

```text
install upstream baseline
create forms
create teams
create sample submissions
switch to fork
migrate
validate all records
```

This test is mandatory before production release.

---

# 12. v16 Compatibility Workstream Deliverables

Create:

```text
docs/
  v16-compatibility.md
  v16-known-issues.md
  v16-test-matrix.md
```

Each issue:

```text
ID
Area
Upstream behavior
Frappe v16 behavior
Reproduction
Root cause
Fix
Regression test
Status
```

---

# 13. v16 Compatibility Release Gate

Before any feature milestone is accepted, all of this must pass:

```text
[ ] clean install
[ ] migrate
[ ] backend tests
[ ] production frontend build
[ ] SPA routes
[ ] Forms app screen
[ ] create form
[ ] edit form
[ ] publish
[ ] guest render
[ ] guest submit
[ ] file upload
[ ] team permission
[ ] archive/unpublish
[ ] no browser console errors
[ ] no Python tracebacks
[ ] no schema mutation
```

---

# 14. Product Domain Architecture

Split the product into clear domains.

```text
forms_pro/
  authoring/
  publishing/
  runtime/
  mapping/
  submissions/
  success/
  themes/
  analytics/
  security/
  compatibility/
```

Do not put all behavior inside the `Form` DocType controller.

---

# 15. Proposed Backend Package Structure

```text
forms_pro/
├── api/
│   └── v1/
│       ├── builder/
│       │   ├── forms.py
│       │   ├── doctypes.py
│       │   ├── preview.py
│       │   ├── publishing.py
│       │   ├── themes.py
│       │   ├── submissions.py
│       │   └── analytics.py
│       │
│       └── public/
│           ├── forms.py
│           ├── submissions.py
│           ├── links.py
│           └── files.py
│
├── services/
│   ├── authoring/
│   │   ├── schema.py
│   │   ├── validator.py
│   │   └── capabilities.py
│   │
│   ├── publishing/
│   │   ├── publisher.py
│   │   ├── versioning.py
│   │   └── compiler.py
│   │
│   ├── mapping/
│   │   ├── engine.py
│   │   ├── generic.py
│   │   ├── scalar.py
│   │   ├── child_table.py
│   │   ├── file.py
│   │   └── adapters/
│   │
│   ├── submissions/
│   │   ├── processor.py
│   │   ├── validator.py
│   │   ├── matcher.py
│   │   └── serializer.py
│   │
│   ├── runtime/
│   │   ├── public_schema.py
│   │   └── conditions.py
│   │
│   ├── success/
│   │   ├── renderer.py
│   │   └── schema.py
│   │
│   ├── security/
│   │   ├── captcha.py
│   │   ├── origins.py
│   │   ├── rate_limit.py
│   │   └── sanitization.py
│   │
│   └── analytics/
│       ├── queries.py
│       └── attribution.py
│
├── compatibility/
│   └── v16.py
│
└── forms_pro/doctype/
    ├── form/
    ├── form_field/
    ├── fp_form_version/
    ├── fp_form_submission/
    ├── fp_form_theme/
    └── forms_pro_settings/
```

Exact paths may follow existing Frappe module conventions, but service boundaries should remain.

---

# 16. Frontend Architecture

Preserve Vue 3.

Proposed:

```text
frontend/src/
├── pages/
│   ├── Dashboard.vue
│   ├── CreateForm.vue
│   ├── FormStudio.vue
│   ├── ManageForm.vue
│   ├── Submissions.vue
│   └── Analytics.vue
│
├── studio/
│   ├── builder/
│   ├── success/
│   ├── design/
│   ├── settings/
│   └── preview/
│
├── runtime/
│   ├── PublicForm.vue
│   ├── FormRenderer.vue
│   └── SuccessRenderer.vue
│
├── fields/
│   ├── registry.ts
│   ├── renderers/
│   ├── editors/
│   └── validators/
│
├── stores/
│   ├── formStudio.ts
│   ├── history.ts
│   ├── publicForm.ts
│   └── user.ts
│
├── api/
│   ├── builder.ts
│   └── public.ts
│
└── utils/
    ├── conditions.ts
    ├── schema.ts
    └── styles.ts
```

---

# 17. Core Data Model

---

# 18. `Form`

Keep the existing DocType but evolve it.

Recommended important fields:

```text
title
target_doctype
team
status
draft_revision
active_version
route
access_mode
login_required
allow_incomplete
submission_mode
record_strategy
success_mode
success_schema_json
theme
theme_overrides_json
allowed_embedding_domains
captcha_enabled
captcha_threshold_override
analytics_enabled
is_archived
```

Compatibility fields:

```text
linked_doctype
is_published
success_title
success_description
```

may remain temporarily during migration.

---

# 19. Form Lifecycle

Replace a simple boolean with:

```text
Draft
Published
Archived
```

Possible internal state model:

```text
Draft
  │
  ├── Publish -> Published
  │
  └── Archive -> Archived

Published
  │
  ├── edit -> Draft changes while old version stays live
  ├── unpublish -> Draft
  └── archive -> Archived

Archived
  │
  └── restore -> Draft
```

Important behavior:

> Editing a published form must not mutate the live version until Publish is clicked again.

---

# 20. `Form Field`

Current child fields are not sufficient for a generic mapping engine.

Add:

```text
field_key
source_type
form_fieldtype
label
description
required
hidden
default
server_default
lock_default
options
conditional_logic
target_fieldname
mapping_type
mapping_config_json
validation_json
appearance_json
row_index
column_index
cell_index
```

---

# 21. Stable `field_key`

Never make labels or target fieldnames the permanent form identity.

Example:

```text
fld_d85fa8d7
```

The public client submits:

```json
{
  "fld_d85fa8d7": "Residential"
}
```

The server version schema knows:

```text
fld_d85fa8d7 -> target field
```

Benefits:

- labels can change,
- mapping can change in draft,
- target fieldname is not exposed unnecessarily,
- conditional logic remains stable,
- versions can be compared.

---

# 22. `source_type`

Values:

```text
Target Field
Form Field
Presentation
System
```

---

## 22.1 Target Field

Uses an existing field from target DocType.

Example:

```text
Target field: subject
Form label: What can we help you with?
```

Changing the form label never changes target field metadata.

---

## 22.2 Form Field

A field that exists only in the form schema.

It may:

```text
map to a target field
remain submission-only
participate in conditions
feed a transform
```

Example:

```text
Question:
How did you hear about us?

Mapping:
target.source
```

---

## 22.3 Presentation

No submitted value.

Examples:

```text
Heading
Paragraph
Divider
Image
Section
Page Break
Spacer
```

---

## 22.4 System

Server-controlled metadata.

Examples:

```text
UTM campaign
source URL
referrer
hidden constant
submission timestamp
```

These values must not be trusted from user-editable controls.

---

# 23. Generic Mapping Types

Use an explicit mapping engine.

```text
Direct
Constant
Transform
Child Table
Table MultiSelect
Attach
Attach Image
No Target
```

---

# 24. Direct Mapping

```text
Form field
   ↓
Target DocField
```

Validate field compatibility at publish time.

Example:

```text
Form Email -> target.email
```

---

# 25. Constant Mapping

Server-controlled constant:

```text
Target.source = "Website Form"
```

The constant comes from published server schema, not browser payload.

---

# 26. Transform Mapping

Architecture extension:

```text
input
  ↓
safe transform
  ↓
target
```

Initial transforms can be predefined:

```text
Trim
Lowercase
Uppercase
Boolean normalize
Number parse
Join
Split
Date normalization
```

Do not support arbitrary Python/JavaScript transform code in public forms for v1.

---

# 27. Child Table Mapping

Support Table fields through a nested/repeating form block.

Example:

```text
Sales Order
  └── items
      ├── item_code
      ├── qty
      └── rate
```

Form schema:

```json
{
  "key": "fld_items",
  "type": "Table",
  "target_field": "items",
  "row_fields": [
    {
      "key": "fld_item",
      "target_field": "item_code"
    },
    {
      "key": "fld_qty",
      "target_field": "qty"
    }
  ]
}
```

Server must validate the child schema from metadata.

Never accept arbitrary child fieldnames from the browser.

---

# 28. Table UI

Builder should provide:

```text
Repeating Group
  ├── Add row button
  ├── Min rows
  ├── Max rows
  ├── Allow remove
  └── Child fields
```

Mobile rendering should use cards rather than a wide grid where appropriate.

---

# 29. Form Submission DocType

Create:

```text
FP Form Submission
```

Core fields:

```text
form
form_version
submitted_at
status
processing_status
target_doctype
target_name
operation
response_json
source_url
referrer
utm_source
utm_medium
utm_campaign
utm_term
utm_content
gclid
error_code
error_summary
retry_count
```

Indexes:

```text
(form, submitted_at)
status
target_doctype
target_name
```

---

# 30. Why Submission Records Are Mandatory

Do not calculate form analytics by counting target documents.

Reasons:

- multiple forms can create same DocType,
- one target document may receive multiple submissions,
- update forms may not create new documents,
- rejected/failed submissions need auditability,
- form version matters,
- attribution belongs to submission, not necessarily target record.

---

# 31. `FP Form Version`

Publishing creates an immutable snapshot.

Fields:

```text
form
version_number
published_at
published_by
schema_json
mapping_json
success_schema_json
theme_json
runtime_settings_json
schema_hash
```

Runtime loads this snapshot.

It should **not** rebuild a published form from current live DocType metadata every request.

---

# 32. Why Immutable Versions Matter

Without versioning:

```text
Target field changes
        ↓
old live form can silently change
```

With versioning:

```text
Draft
  ↓ publish
Version 7
  ↓
Public runtime stays Version 7
```

Later edits produce Version 8 only after explicit Publish.

---

# 33. Schema Compiler

At publish time compile:

```text
Draft Form DocType
+
Form Fields
+
Target DocType metadata
+
Theme
+
Success design
+
Security settings
```

into:

```text
Immutable Public Runtime Schema
```

This compiler is one of the core architectural pieces.

---

# 34. Form Field Capability Registry

Do not scatter field behavior across components.

Frontend registry:

```ts
interface FieldDefinition {
  type: string
  category: string
  renderer: Component
  editor: Component
  storesValue: boolean
  supportsOptions: boolean
  supportsDefault: boolean
  supportsRequired: boolean
  supportedTargetTypes: string[]
}
```

Backend equivalent validates the same capability.

---

# 35. Field Support Strategy

## Native/simple

```text
Data
Small Text
Text
Long Text
Text Editor
Int
Float
Currency
Percent
Check
Select
Date
Datetime
Time
Duration
Phone
Rating
Color
```

---

## Files

```text
Attach
Attach Image
```

Need controlled upload pipeline.

---

## Relational

```text
Link
Dynamic Link
```

Need restricted server-side option search.

---

## Collections

```text
Table
Table MultiSelect
```

Need nested mapping.

---

## Presentation

```text
Heading
Paragraph
Divider
Image
Section
Columns
Page Break
Spacer
```

---

## Unsupported/system field types

The builder should not crash.

Display them under:

```text
Unavailable fields
```

with explanation.

Example:

```text
Read Only
HTML generated fields
Button
Column Break as target data
Section Break as target data
Tab Break as target data
```

Layout equivalents are available as Forms Pro presentation blocks instead.

---

# 36. DocType Selection UX

Create Form wizard:

```text
Step 1
What should this form create/update?

[ Search DocTypes... ]

Recent
  Lead
  Issue
  Customer

All available
  ...

Custom DocTypes
  ...
```

Do not show every internal Frappe DocType indiscriminately.

API returns only targets permitted by:

```text
System policy
User builder permission
DocType capability
denylist
```

---

# 37. DocType Capability Inspector

After target selection show:

```text
Target: Issue

✓ Can create
✓ Can update
✓ Supports attachments
✓ Standard DocType
✓ Not submittable
2 mandatory target fields not yet mapped
```

For special DocTypes:

```text
Target: Some Submittable DocType

✓ Can create draft
⚠ Document can be submitted
⚠ 3 mandatory fields required by server
```

---

# 38. Builder UX — Form Studio

Recommended top-level studio:

```text
┌──────────────────────────────────────────────────────────────┐
│ ← Forms   Draft saved 3s ago         Preview     Publish    │
├──────────────────────────────────────────────────────────────┤
│ Build | Success | Design | Settings                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Left Panel       Canvas                     Properties      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

One product, one consistent editing experience.

---

# 39. Build Tab

Left field palette:

```text
TARGET FIELDS
  Search target fields...

BASIC
  Short text
  Long text
  Number
  Email
  Phone

CHOICE
  Select
  Multi-select
  Checkbox
  Switch
  Rating

DATE & TIME
  Date
  Date time
  Time

RELATION
  Link

UPLOAD
  File
  Image

LAYOUT
  Heading
  Paragraph
  Divider
  Image
  Section
  Columns
  Page break
  Spacer

ADVANCED
  Repeating group
```

---

# 40. Target Field Picker

A target field item should show:

```text
Customer Name
Data
customer_name
```

but fieldname should be secondary.

Status chips:

```text
Required by target
Already used
Read only
Unsupported
Child table
```

Search by:

```text
label
fieldname
field type
```

---

# 41. Field Properties Panel

Common:

```text
Label
Help text
Placeholder
Required on form
Hidden
Default
Width
Description
```

Mapping:

```text
Save answer to
Mapping type
Target field
```

Validation:

```text
Minimum
Maximum
Length
Pattern
Allowed values
```

Conditional:

```text
Show when
Hide when
Require when
```

Appearance:

```text
Field width
Label alignment
Help position
```

---

# 42. Required Fields

Different concepts:

```text
Target Required
Form Required
Conditionally Required
```

The UI should explain them clearly.

Example:

```text
Required by DocType  [locked indicator]
Required on this form [toggle]
```

If a target-required field is not present:

```text
Publish blocker:
"Customer Name is mandatory in Customer but is not mapped or provided by a server default."
```

---

# 43. Hidden Fields / Preset Values

Client requirement:

```text
Language = German
hidden
```

Generic design:

```text
Hidden field
Target field: language
Value source: Constant
Value: German
Lock value: Yes
```

Server wins over browser payload.

---

# 44. Form-Only Field Mapping

User creates:

```text
Question:
Where will the system be installed?
```

Then:

```text
Save answer to:
[ Target DocType → system_type_interest ]
```

This is a generic feature.

Nothing in the implementation should mention Contact.

---

# 45. Conditional Logic

Use `field_key`, never label/fieldname identity.

Example:

```json
{
  "all": [
    {
      "field": "fld_property_type",
      "operator": "equals",
      "value": "Commercial"
    }
  ]
}
```

Supported operators:

```text
equals
not equals
contains
does not contain
is empty
is not empty
greater than
less than
in
not in
```

---

# 46. Condition Editor UX

```text
Show this field when:

[ Property Type ▼ ] [ equals ▼ ] [ Commercial ▼ ]

+ Add condition

Match:
○ All
○ Any
```

No JSON editing required for normal users.

---

# 47. Multi-Page Forms

Use Page Break as an authoring block.

Builder page tabs:

```text
Page 1
Page 2
Page 3
+ Add page
```

Page settings:

```text
Title
Description
Show progress
Next button label
Back button label
```

Validation happens per step and again on final server submission.

---

# 48. Undo / Redo

Add form-builder history store.

Shortcuts:

```text
Ctrl/Cmd + Z
Ctrl/Cmd + Shift + Z
```

History operations:

```text
add field
delete field
move field
change properties
change layout
change theme
edit success page
```

Do not create database writes for every undo step.

---

# 49. Autosave

Draft autosave:

```text
debounce 1–2 seconds after changes
```

UI:

```text
Saving...
Saved
Offline / retry
Save failed
```

Publish remains explicit.

Draft autosave must not affect current published version.

---

# 50. Builder Dirty-State Safety

On route leave/browser close:

```text
if unsaved changes:
  warn
```

Autosave reduces but does not eliminate need for protection.

---

# 51. Duplicate Field

Context menu:

```text
Duplicate
Delete
Move to page
```

Duplicate generates a new:

```text
field_key
```

and preserves configuration except unique mapping conflicts.

---

# 52. Field Search and Categories

The left panel can become large.

Provide:

```text
Search
Favorites
Recently used
Target fields
Basic
Advanced
Layout
```

---

# 53. Mobile Builder

Full drag/drop desktop builder is the main editing surface.

On small screens:

```text
limited property editing
preview
publish/unpublish
submission viewing
```

Do not force a complex 3-pane builder into a phone-sized layout.

---

# 54. Design System / Theme Editor

Client requires:

```text
colors
shapes
fonts
corporate design
```

Use safe theme tokens rather than requiring CSS.

---

# 55. Theme Data

Create:

```text
FP Form Theme
```

or store reusable theme JSON.

Recommended tokens:

```json
{
  "font_family": "Inter",
  "font_size": "16px",
  "heading_font_family": "Inter",
  "text_color": "#111827",
  "muted_text_color": "#6B7280",
  "background_color": "#FFFFFF",
  "surface_color": "#FFFFFF",
  "primary_color": "#1D4ED8",
  "primary_hover_color": "#1E40AF",
  "input_background": "#FFFFFF",
  "input_border_color": "#D1D5DB",
  "input_focus_color": "#2563EB",
  "input_radius": "8px",
  "button_radius": "8px",
  "card_radius": "12px",
  "form_max_width": "720px",
  "field_gap": "16px",
  "section_gap": "28px"
}
```

---

# 56. Design Tab UX

```text
Design

Theme
[ Corporate Blue ▼ ]

Typography
  Body font
  Heading font
  Font size
  Label weight

Colors
  Background
  Text
  Primary
  Field border

Fields
  Radius
  Height
  Border width
  Shadow

Button
  Radius
  Height
  Alignment
  Full width

Layout
  Max width
  Section gap
  Field gap
```

Every change previews instantly.

---

# 57. Reusable Themes

Allow:

```text
Save as Theme
Apply Theme
Duplicate Theme
```

This is important when the client has many site forms.

---

# 58. Advanced CSS

Possible later.

If included:

```text
System Manager only
```

Sanitize/limit where feasible.

Do not make arbitrary CSS mandatory for normal users.

---

# 59. Success Page Designer — First-Class Feature

Success experience should not be only:

```text
success_title
success_description
```

Create a visual success-page editor.

Studio top tab:

```text
Build | Success | Design | Settings
```

---

# 60. Success Modes

```text
After successful submission:

○ Show designed success page
○ Redirect to another URL
```

Optional future:

```text
○ Conditional success page
```

---

# 61. Success Builder

Use the same canvas principles as form builder.

Blocks:

```text
Success Icon
Heading
Paragraph / Rich Text
Image
Divider
Spacer
Button / CTA
Secondary Button
Submission Reference
Selected Response Summary
Next Steps List
```

Do not allow arbitrary script blocks.

---

# 62. Success Page Example

```text
✓

Thank you!

We received your request successfully.

Reference:
SUB-000234

[ Back to website ]
```

---

# 63. Success Page Design

By default:

```text
inherit form theme
```

Allow overrides:

```text
background
alignment
max width
icon style
heading size
CTA layout
```

---

# 64. Success Page Dynamic Variables

Allow safe merge tags:

```text
{{ submission_id }}
{{ form_title }}
```

Optionally selected form responses:

```text
{{ field.fld_first_name }}
```

All output must be escaped/sanitized.

Never support unrestricted Jinja execution from form designers.

---

# 65. Success Redirect

Settings:

```text
Redirect URL
Redirect immediately / after delay
Pass submission reference? yes/no
Preserve UTM? yes/no
```

Never append personal form values to URL automatically.

Safe query example:

```text
?submission=FPSUB-0001
```

only if explicitly enabled.

---

# 66. Conversion Integrity

Do not expose a static public success URL that can be loaded directly and counted as a conversion.

For internal success rendering:

```text
submission success
  ↓
server returns receipt
  ↓
client renders success state
```

If a dedicated success route is later required, use a signed short-lived receipt token.

---

# 67. Preview Experience

Top button:

```text
Preview
```

Open modal/full-page preview.

Modes:

```text
Desktop
Tablet
Mobile
```

Preview tabs:

```text
Form
Success Page
```

Draft preview uses current draft schema.

No target records should be created from preview unless:

```text
Test Submission Mode
```

is explicitly enabled.

---

# 68. Test Submission Mode

Useful for UAT.

In preview:

```text
[ Test submission ]
```

Behavior:

```text
validate everything
render success page
DO NOT create target record
optionally create test-marked FP Submission
```

Clearly mark:

```text
TEST
```

in logs/analytics exclusion.

---

# 69. Publishing Model

Publish button opens a review panel.

```text
Ready to publish?

Target: Issue
Route: support-request
Access: Public
CAPTCHA: Enabled
Embed domains: 2

Validation
✓ 8 fields valid
✓ required target fields satisfied
✓ success page configured
✓ route unique
✓ no unsupported mapping
```

Then:

```text
Publish Version 4
```

---

# 70. Publish Validation

Block publishing if:

```text
target DocType unavailable
target field removed
required target field unsatisfied
invalid mapping
duplicate scalar mapping conflict
invalid Link configuration
invalid child-table mapping
hidden required field lacks default
invalid route
route collision
invalid embed origin
invalid redirect URL
CAPTCHA globally required but not configured
success mode incomplete
```

Warnings may include:

```text
unused target field
large number of fields
very large file limit
no success CTA
```

Warnings do not necessarily block publish.

---

# 71. Standalone Public Form

Published form:

```text
/forms/p/<route>
```

Features:

```text
responsive
theme
multi-page
conditional logic
files
CAPTCHA
success builder
redirect
analytics
```

---

# 72. External Website Embed

Preferred architecture:

```text
external site
   │
   └── embed.js
          │
          └── creates iframe
                  │
                  └── /forms/p/<route>?embed=1
```

This is better than directly mounting Vue into the customer's DOM because:

- CSS isolation,
- JS isolation,
- no Vue version collision,
- easier upgrades,
- same-origin API calls inside iframe,
- simpler security.

---

# 73. Embed Snippet

User-facing:

```html
<div data-forms-pro="solar-request"></div>
<script
  async
  src="https://crm.example.com/assets/forms_pro/embed.js">
</script>
```

Alternative advanced:

```html
<iframe
  src="https://crm.example.com/forms/p/solar-request?embed=1"
  width="100%"
  frameborder="0">
</iframe>
```

---

# 74. Important Embed Security Advantage

If submission happens **inside the Frappe-hosted iframe**, then:

```text
iframe page origin = Frappe origin
submission API origin = Frappe origin
```

Therefore the public submission flow does **not** need to expose broad cross-origin API CORS just because the form is embedded.

The parent website only communicates using controlled `postMessage`.

This is the preferred design.

---

# 75. Embed Messaging Protocol

Events:

```text
formspro:ready
formspro:resize
formspro:started
formspro:submitted
formspro:redirect
formspro:error
```

Example:

```json
{
  "source": "forms-pro",
  "event": "formspro:submitted",
  "form": "solar-request",
  "submission_id": "FPSUB-00023"
}
```

Never send:

```text
email
phone
address
full response payload
```

through parent events.

---

# 76. Auto Height

Iframe sends:

```json
{
  "event": "formspro:resize",
  "height": 684
}
```

Parent changes iframe height smoothly.

Trigger after:

```text
load
field condition change
validation errors
page change
success page render
```

---

# 77. Allowed Embed Origins

Form setting:

```text
Allowed websites

https://example.com
https://landing.example.com
```

Validate exact origins.

Do not accept:

```text
example.com.evil.com
```

through substring checks.

Normalize:

```text
scheme
hostname
port
```

---

# 78. CSP / Frame Policy

Embedding needs infrastructure review for:

```text
Content-Security-Policy
frame-ancestors
X-Frame-Options
```

The form route should allow only configured parents.

Do not globally weaken iframe protections for the entire Frappe site.

---

# 79. Public API Architecture

Keep public surface minimal.

Recommended method namespace:

```text
forms_pro.api.v1.public.forms.get
forms_pro.api.v1.public.submissions.submit
forms_pro.api.v1.public.links.search
forms_pro.api.v1.public.files.start
forms_pro.api.v1.public.files.upload
```

---

# 80. Builder API Architecture

Authenticated:

```text
forms_pro.api.v1.builder.forms.list
forms_pro.api.v1.builder.forms.get
forms_pro.api.v1.builder.forms.create
forms_pro.api.v1.builder.forms.save
forms_pro.api.v1.builder.forms.validate
forms_pro.api.v1.builder.forms.publish
forms_pro.api.v1.builder.forms.unpublish
forms_pro.api.v1.builder.forms.archive
forms_pro.api.v1.builder.forms.restore
forms_pro.api.v1.builder.forms.duplicate

forms_pro.api.v1.builder.doctypes.search
forms_pro.api.v1.builder.doctypes.get_schema

forms_pro.api.v1.builder.preview.get_token

forms_pro.api.v1.builder.submissions.list
forms_pro.api.v1.builder.submissions.get
forms_pro.api.v1.builder.submissions.retry

forms_pro.api.v1.builder.analytics.summary
forms_pro.api.v1.builder.analytics.timeseries
```

---

# 81. Public Form GET Response

Only return data required to render.

Example:

```json
{
  "form": {
    "id": "FORM-0001",
    "route": "support-request",
    "version": 4,
    "title": "Support Request"
  },
  "schema": [
    {
      "key": "fld_name",
      "type": "Data",
      "label": "Your name",
      "required": true
    }
  ],
  "theme": {},
  "success": {},
  "security": {
    "captcha": true,
    "captcha_site_key": "public-key"
  }
}
```

Do not expose internal mapping if browser does not need it.

---

# 82. Public Submit Request

```json
{
  "route": "support-request",
  "version": 4,
  "values": {
    "fld_name": "Anna",
    "fld_issue": "Installation"
  },
  "tracking": {
    "source_url": "https://example.com/support",
    "referrer": "https://google.com/",
    "utm_source": "google"
  },
  "captcha_token": "..."
}
```

---

# 83. Public Submit Pipeline

```text
Request
  ↓
Resolve route
  ↓
Load active immutable version
  ↓
Check form status
  ↓
Rate limit
  ↓
Validate origin/embed context
  ↓
Verify CAPTCHA
  ↓
Filter unknown field keys
  ↓
Apply server constants/hidden defaults
  ↓
Validate conditions
  ↓
Validate types/options
  ↓
Validate mapping
  ↓
Create FP Form Submission
  ↓
Execute record strategy
  ↓
Map to target DocType
  ↓
Run Frappe target validation
  ↓
Save / update / submit
  ↓
Link target to FP Submission
  ↓
Mark processed
  ↓
Return receipt + success instructions
```

---

# 84. Never Accept Target Metadata from Public Client

Never trust payload like:

```json
{
  "doctype": "User",
  "fieldname": "enabled"
}
```

Public client provides only:

```text
route
version
field_key -> value
```

Server derives:

```text
target DocType
target fields
mapping
defaults
record strategy
```

from immutable version.

---

# 85. Generic Record Strategies

Form setting:

```text
Submission action
```

Values:

```text
Create New
Update Existing
Create or Update
Collect Submission Only
```

---

# 86. Create New

```python
doc = frappe.new_doc(target_doctype)
apply_mappings(doc)
doc.insert(...)
```

Do not allow browser to specify target DocType.

---

# 87. Update Existing

Requires a record resolution rule.

Possible sources:

```text
Authenticated document context
Secure signed document token
Configured match rule
```

Never accept unrestricted:

```text
docname
```

from anonymous user without authorization.

---

# 88. Create or Update

Builder config:

```text
Match existing by:
[ Email ▼ ]

If found:
○ overwrite non-empty values
○ fill empty fields only
○ do not update target
```

This is generic.

Matching rules should support a controlled set:

```text
exact field
multiple fields AND
normalized value
```

Do not implement arbitrary query expressions for non-admin form designers.

---

# 89. Collect Submission Only

Useful for:

```text
survey
temporary intake
manual review
```

No target document created.

Later action can convert a submission into a target document.

---

# 90. Mapping Engine

Core interface:

```python
class MappingEngine:
    def validate_schema(...)
    def create_target(...)
    def resolve_existing(...)
    def apply_scalar_fields(...)
    def apply_child_tables(...)
    def apply_files(...)
    def finalize(...)
```

---

# 91. Target Adapter Interface

Most DocTypes use generic adapter.

```python
class TargetAdapter:
    supports_create: bool
    supports_update: bool
    supports_submit: bool

    def inspect_capabilities(...)
    def validate_mapping(...)
    def find_existing(...)
    def prepare_document(...)
    def after_mapping(...)
    def persist(...)
```

Only add specialized adapters when a DocType truly has special semantics.

Do not put DocType-specific `if target == ...` logic across multiple services.

---

# 92. Generic Adapter

Handles ordinary fields using Frappe metadata:

```text
Data
Text
Numeric
Check
Select
Date/Time
Link
Attachments
Child tables
```

This should cover the majority of standard/custom DocTypes.

---

# 93. Field Compatibility Validation

At publish:

```text
Form Email
  ↓
Target Data(options=Email)
  -> compatible

Form Number
  ↓
Target Int
  -> compatible with integer validation

Form Textarea
  ↓
Target Date
  -> incompatible
```

Prevent invalid forms before they go live.

---

# 94. Link Field Security

Public Link field must never call:

```text
search arbitrary DocType supplied by browser
```

Instead:

```text
route + version + field_key + search text
```

Server:

```text
load published field
read configured Link target
apply allowed query/filter
return safe options
```

---

# 95. Link Search Response

Return minimal:

```json
[
  {
    "value": "CUST-0001",
    "label": "Example Customer"
  }
]
```

Do not expose entire linked documents.

---

# 96. Dynamic Link

Only enable when the form schema controls both:

```text
dynamic target type
allowed values
```

Public users must not turn Dynamic Link into arbitrary DocType enumeration.

---

# 97. File Upload Architecture

Public file upload is security-sensitive.

Preferred approach:

```text
Initialize upload session
       ↓
server issues signed short-lived token
       ↓
upload file for a specific field_key
       ↓
server validates form/version/field
       ↓
temporary private File
       ↓
final submit claims file
       ↓
attach to submission/target
```

---

# 98. Upload Session

Use Redis/cache or a small temporary record.

Token contains/represents:

```text
form
version
field_key
expiry
nonce
```

Files not claimed by completed submission are cleaned after TTL.

---

# 99. File Validation

Server enforces:

```text
maximum bytes
extension allowlist
MIME validation where practical
number of files
private/public
field permits upload
```

Never trust filename extension only.

---

# 100. File Field Settings

```text
Allowed types
Maximum size
Maximum files
Private file
Map to target Attach field?
```

If no target field:

```text
keep attachment on FP Form Submission
```

---

# 101. Security Baseline

Public forms require layered security.

```text
Published-version allowlist
CAPTCHA
Rate limit
Origin policy
Schema filtering
Server-side validation
File validation
Output sanitization
No arbitrary target metadata
No unsafe Link enumeration
```

---

# 102. CAPTCHA

Client requires invisible CAPTCHA.

Recommended first implementation:

```text
Google reCAPTCHA v3
```

Architecture:

```text
browser obtains token
      ↓
submit API
      ↓
server verifies with provider
      ↓
check success/action/hostname/score
```

---

# 103. CAPTCHA Settings

Singleton:

```text
Forms Pro Settings
```

Fields:

```text
captcha_provider
recaptcha_site_key
recaptcha_secret_key
default_score_threshold
require_captcha_for_public_forms
```

Form override:

```text
captcha_enabled
captcha_score_threshold
```

Secret key must never be returned to browser.

---

# 104. Rate Limiting

Apply rate limiting even when CAPTCHA is enabled.

Suggested initial public submit:

```text
10 requests / minute / relevant limiter key
```

Tune based on production behavior.

Also rate-limit:

```text
Link search
upload initialization
file upload
preview token requests
```

---

# 105. Guest Schema Exposure

Upstream issue documents that `get_doctype_fields` can expose arbitrary DocType schema to guests.

Our fork should go further than the minimal upstream proposal.

Preferred design:

```text
Builder:
  authenticated get_doctype_schema

Public:
  get_public_form only
```

Guest never needs complete target DocType metadata.

---

# 106. XSS / Rich Text

Sanitize:

```text
Form descriptions
Paragraph blocks
Success rich text
Help text if HTML supported
```

Do not allow arbitrary:

```html
<script>
```

from normal form designers.

---

# 107. Success Page Tracking

After server confirms submission:

```text
formspro:submitted
```

is emitted.

For embed parent:

```javascript
window.dataLayer?.push({
  event: "formspro_form_submit",
  form_name: "support-request",
  submission_id: "FPSUB-00023"
})
```

Do not include PII.

---

# 108. Google Analytics / Ads

Support two reliable patterns.

## Pattern A — External thank-you URL

```text
submit
  ↓
success
  ↓
redirect customer website /thank-you
```

Customer tracks page view/conversion normally.

## Pattern B — Embedded event

```text
iframe submit
  ↓
postMessage
  ↓
embed.js
  ↓
CustomEvent + dataLayer
```

This works without redirecting the parent page.

---

# 109. Analytics Architecture

MVP should answer:

```text
How many successful submissions happened during a date range?
```

Use `FP Form Submission`.

---

# 110. Analytics Dashboard

Cards:

```text
Submissions
Successful
Failed
Spam/Rejected
Target records created
Target records updated
```

Filters:

```text
Today
7 days
30 days
90 days
Custom range
Form version
Source
Campaign
Status
```

---

# 111. Time Series

Chart:

```text
Date -> successful submissions
```

Optional secondary:

```text
Created vs Updated
```

---

# 112. Submission Browser

Columns:

```text
Submitted At
Status
Target DocType
Target Record
Operation
Source
Campaign
Version
```

Allow:

```text
filter
search
open
retry failed
```

Permissions apply.

---

# 113. Attribution

Capture:

```text
source URL
referrer
utm_source
utm_medium
utm_campaign
utm_term
utm_content
gclid
```

For embed, parent script can pass safe parent page metadata.

Do not treat tracking metadata as trusted target-field data unless explicitly mapped by server configuration.

---

# 114. Optional View/Start Analytics

Future:

```text
form_view
form_start
page_change
form_submit
```

Can support conversion rate.

Not required for initial client requirement.

Keep event logging separate from response data to avoid analytics table explosion too early.

---

# 115. Archive

Archive preserves:

```text
Form
Versions
Submissions
Analytics
```

Disables:

```text
new public submissions
embed
```

Restoring:

```text
Archived -> Draft
```

Require republish after validation.

---

# 116. Duplicate Form

Duplicate:

```text
fields
layout
mapping
conditions
theme
success design
security defaults
```

Do not copy:

```text
route
active version
submissions
analytics
```

New copy starts Draft.

---

# 117. Dashboard UI Enhancement

Current dashboard should become more useful.

Recommended:

```text
Forms                                + New Form

Search...

Filters:
All | Published | Draft | Archived

Sort:
Recently updated
Recently created
Name
Most submissions
```

Card:

```text
Support Request
Published

Issue
23 submissions this month

Updated 2h ago

[Edit] [Analytics] [...]
```

---

# 118. New Form Wizard

Flow:

```text
1. Choose target DocType
2. Choose Blank / Template
3. Name + route
4. Choose record strategy
5. Open Studio
```

Avoid showing advanced settings during first creation.

---

# 119. Ease-of-Use Principles

Normal form designer should not need to understand:

```text
DocField JSON
Python
Frappe internals
fieldname syntax
Custom Field
hooks
API routes
CSS
```

Expose technical detail only when useful.

---

# 120. Builder Warnings

Inline warnings are better than final errors.

Example:

```text
⚠ This target field is mandatory.
```

```text
⚠ This field has already been mapped.
```

```text
⚠ Link fields require a public option policy.
```

---

# 121. Field Mapping Visualization

Right panel:

```text
FORM
Where does this get installed?
          │
          ▼
TARGET
System Type Interest
```

Use clear chips.

---

# 122. Accessibility

Public runtime should target:

```text
keyboard navigation
visible focus
proper labels
aria-describedby
error summaries
screen-reader error association
sufficient contrast
responsive zoom
```

Builder should also support keyboard selection and property editing where practical.

---

# 123. Dark Mode

Builder should follow Frappe/user theme.

Public form theme is independent and controlled by form theme.

Do not automatically force public form to browser dark mode unless configured.

---

# 124. Localization

Architecture should support translated presentation later.

Do not use target DocType labels as the only source of rendered text.

Because form labels are form-owned, future model can support:

```text
English label
German label
French label
```

without modifying target metadata.

---

# 125. Published Schema Example

Internal published snapshot:

```json
{
  "form": "FORM-001",
  "version": 4,
  "target": {
    "doctype": "Issue",
    "strategy": "Create New"
  },
  "fields": [
    {
      "key": "fld_subject",
      "source_type": "Target Field",
      "type": "Data",
      "label": "What do you need help with?",
      "required": true,
      "mapping": {
        "type": "Direct",
        "target_field": "subject"
      }
    },
    {
      "key": "fld_language",
      "source_type": "System",
      "type": "Data",
      "hidden": true,
      "mapping": {
        "type": "Constant",
        "target_field": "language",
        "value": "German"
      }
    }
  ],
  "success": {},
  "theme": {},
  "security": {}
}
```

Public schema can remove internal mapping.

---

# 126. Do Not Store Secrets in Published Client Schema

Server-only:

```text
target field mapping where browser doesn't need it
CAPTCHA secret
internal match rules
permission policy
server constants
private defaults
```

Client:

```text
rendering metadata only
CAPTCHA site key
```

---

# 127. Permission Model

Roles:

```text
Forms Pro User
Forms Pro Manager
System Manager
```

---

## 127.1 Forms Pro User

Can:

```text
view shared/team forms
edit allowed draft forms
view allowed submissions
```

---

## 127.2 Forms Pro Manager

Can:

```text
create form
publish
archive
configure target mapping
manage themes
view analytics
```

---

## 127.3 System Manager

Can:

```text
configure global settings
CAPTCHA secrets
DocType allow/deny policy
advanced mapping capability
security settings
```

---

# 128. Target DocType Permission Strategy

Builder permission and public submission permission are separate.

Builder must have authorization to design against a target DocType.

Public submit does not require giving Guest direct create permission on that DocType.

Instead:

```text
Guest
  ↓
Forms Pro controlled endpoint
  ↓
published mapping allowlist
  ↓
server creates target
```

Using `ignore_permissions=True` is acceptable only inside a tightly controlled service after all server-side schema validation.

It must never be used with browser-supplied DocType/field names.

---

# 129. Forms Pro Settings

Create singleton:

```text
Forms Pro Settings
```

Sections:

```text
General
Security
CAPTCHA
Uploads
Embedding
Analytics
Advanced
```

Examples:

```text
Allowed target modules
Denied target DocTypes
Require CAPTCHA for public forms
Default file size
Default embed policy
Analytics retention
Allow advanced CSS
```

---

# 130. Migration of Existing Forms Pro Data

Do not assume a clean site.

Before migration:

```bash
bench --site <site> backup --with-files
```

---

# 131. Existing Form Fields

For each field:

If fieldname exists on target:

```text
source_type = Target Field
target_fieldname = current fieldname
field_key = generated
```

If no target field:

```text
source_type = Form Field
mapping = Needs Review
```

Do not guess a target field from label alone.

---

# 132. Existing Forms Pro-Created Custom Fields

Do not automatically delete them.

Generate an audit:

```text
DocType
fieldname
created by Forms Pro?
contains data?
used by active forms?
```

Cleanup is a separate migration decision.

---

# 133. Existing `fp_linked_form` / `fp_submission_status`

Keep during transition if production data depends on them.

New architecture should stop requiring them.

Later release may deprecate them after migration verification.

---

# 134. Migration Patches

Example:

```text
forms_pro.patches.v16_0.add_field_keys
forms_pro.patches.v16_0.add_mapping_fields
forms_pro.patches.v16_0.migrate_existing_mappings
forms_pro.patches.v16_0.add_form_status
forms_pro.patches.v16_0.add_form_versions
forms_pro.patches.v16_0.create_submission_doctype_data
```

Patches must be:

```text
safe
idempotent where practical
non-destructive
tested on copied production data
```

---

# 135. Fork Strategy

Git remotes:

```text
origin   = company fork
upstream = bwhtech/forms_pro
```

Branches:

```text
version-16
develop
feature/*
hotfix/*
sync/upstream-YYYY-MM
```

Tag exact initial upstream commit:

```text
upstream-baseline-YYYY-MM-DD
```

---

# 136. Upstream Sync

Do not continuously merge `upstream/develop` into production.

Process:

```text
fetch
review commits
identify useful fixes
integration branch
tests
merge/cherry-pick
```

Keep custom architecture separated so upstream UI fixes remain easier to adopt.

---

# 137. Do Not Rename App Package Initially

Keep:

```text
forms_pro
```

to reduce:

- migration complexity,
- asset path changes,
- DocType module changes,
- hooks changes,
- upstream merge conflicts.

Product branding can change in UI without package rename.

---

# 138. Testing Strategy

Testing has five levels.

```text
Unit
Backend integration
Frontend component
End-to-end
Migration/upgrade
```

---

# 139. Critical Non-Destructive Regression Test

Mandatory:

```text
1. create target DocType field:
   label = Original Label
   reqd = 0
   options = A/B

2. add to form

3. change form:
   label = Website Label
   required = true
   help = Website Help
   default = A

4. save form

5. assert target metadata unchanged
```

Run for:

```text
label
fieldtype
required
options
description
default
fieldname
```

---

# 140. Generic Mapping Tests

Use several DocTypes.

Example test targets:

```text
simple custom DocType
standard non-submittable DocType
submittable custom DocType
DocType with Link
DocType with Attach
DocType with child Table
```

Avoid writing the suite around only one business DocType.

---

# 141. Public API Security Tests

Test:

```text
unknown form
draft form
archived form
old invalid version
arbitrary field key
arbitrary target field
arbitrary DocType
hidden field tampering
invalid select value
invalid Link value
CAPTCHA missing
rate limited
file attack cases
```

---

# 142. Builder Tests

Test:

```text
add field
move
delete
duplicate
undo
redo
autosave
mapping
conditional logic
page break
theme
success page
publish errors
```

---

# 143. E2E Core Scenario

```text
Login
→ Create Form
→ choose generic custom DocType
→ add target fields
→ add form-only field
→ map form-only field
→ add hidden constant
→ create success page
→ apply theme
→ preview
→ publish
→ open public route
→ submit
→ success page
→ target document exists
→ FP Submission exists
→ analytics count increments
```

---

# 144. Embed E2E

External test page:

```text
load embed.js
iframe created
ready event
height correct
condition changes height
submit
parent receives submitted event
success page height correct
```

---

# 145. v16 CI Matrix

At minimum:

```text
Python 3.14
Node 24
Frappe version-16
ERPNext version-16 where installed
MariaDB production version
Chrome
Firefox
```

If PostgreSQL support is a real deployment requirement, add it explicitly.

---

# 146. CI Checks

Backend:

```text
ruff
Frappe integration tests
security/static checks
```

Frontend:

```text
yarn install --frozen-lockfile
typecheck
lint
unit tests
build
```

E2E:

```text
Playwright smoke
```

Release:

```text
fresh install test
upgrade test
migration test
```

---

# 147. Performance Architecture

Runtime should not fetch entire target DocType schema on every public request.

Use immutable published version.

Cache:

```text
route -> active version
active public schema
```

Invalidate cache on:

```text
publish
unpublish
archive
```

---

# 148. Analytics Performance

Index:

```text
form
submitted_at
status
```

Use aggregate queries.

Do not deserialize entire response JSON for submission-count reports.

---

# 149. Public Bundle Size

Builder code is large and not needed by visitors.

Create separate chunks/build boundaries for:

```text
Builder
Public Runtime
Embed helper
```

Public form should not download all builder components.

---

# 150. Error Handling

Public response should use stable error codes.

Example:

```json
{
  "ok": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "fields": {
      "fld_email": "Enter a valid email address"
    }
  }
}
```

Do not return traceback.

---

# 151. Error Codes

Recommended:

```text
FORM_NOT_FOUND
FORM_NOT_PUBLISHED
FORM_VERSION_MISMATCH
VALIDATION_ERROR
CAPTCHA_FAILED
RATE_LIMITED
UPLOAD_REJECTED
LINK_NOT_ALLOWED
TARGET_VALIDATION_FAILED
SUBMISSION_FAILED
```

---

# 152. Observability

Structured server logs for:

```text
publish failure
mapping failure
target validation
target save
upload
CAPTCHA
embed-origin denial
submission retry
```

Avoid logging full personal response payloads.

---

# 153. Retry Failed Submission

Managers may retry only processing failures where the original validated submission is safe.

Example:

```text
target save transient failure
```

Do not automatically retry:

```text
CAPTCHA failure
invalid input
spam
```

---

# 154. Privacy

Store only required information.

Do not persist:

```text
raw CAPTCHA tokens
browser fingerprints
unnecessary IP addresses
arbitrary headers
```

If abuse-control metadata is added, define retention.

---

# 155. Client Requirement Mapping

| Client Requirement | Current Forms Pro | Fork Plan |
|---|---|---|
| Multiple website forms | Yes | Keep and improve dashboard/duplicate |
| Standalone page | Yes | Harden v16 runtime |
| Embed code | Upstream enhancement/open work | iframe + embed.js |
| Drag/drop editor | Yes | UX redesign and stabilization |
| Use every relevant DocType field | Partial | Generic field capability engine |
| Form-specific label | Dangerous because schema sync | Non-destructive form metadata |
| Custom question mapped to existing field | Needs architecture | Generic mapping engine |
| Mandatory | Existing | Separate form vs target requirements |
| Hidden preset | Existing basics | Server-authoritative constants |
| Titles/text | Heading support | Rich presentation blocks |
| Help text | Existing description | Improved UX |
| File upload | Existing field type | Secure upload service |
| Colors/shapes/fonts | Limited | Theme designer |
| Publish | Existing boolean | Versioned publishing |
| Preview | Existing concept | Full responsive draft/success preview |
| Archive | Missing/limited | Draft/Published/Archived |
| Invisible reCAPTCHA | Missing | reCAPTCHA v3 |
| Submission counts | Not sufficient | FP Submission analytics |
| Thank-you experience | Title/description | Full success-page designer |
| Thank-you redirect | Needs expansion | Redirect mode |
| GA / Ads | Missing | dataLayer / CustomEvent / external redirect |
| Any DocType | Concept exists | Generic target capability engine |
| Child tables | Requires robust mapping | Repeating-group mapping |
| No DocType pollution | Current implementation conflicts | Remove schema mutation/injected fields |
| v16 compatibility | Declared but not guaranteed | Dedicated compatibility program |

---

# 156. UI Enhancement Roadmap

## Dashboard

```text
search
status filters
target DocType filter
team filter
sort
quick analytics
duplicate
archive
```

## Studio

```text
Build
Success
Design
Settings
```

## Builder

```text
better field palette
target field search
mapping visualization
undo/redo
autosave
warnings
keyboard shortcuts
```

## Preview

```text
desktop/tablet/mobile
form/success
test submission
```

## Publish

```text
validation checklist
route
embed settings
copy link
copy embed
version summary
```

## Manage

```text
overview
submissions
analytics
versions
settings
```

---

# 157. Settings Tab

Sections:

```text
General
Target
Submission
Access
Embedding
Security
Tracking
Advanced
```

Do not put all settings in one long form.

---

# 158. General Settings

```text
Form title
Internal name
Description
Route
```

---

# 159. Target Settings

```text
Target DocType
Record strategy
Match rule
Update behavior
Submittable behavior
```

Changing target after fields exist should require confirmation and remapping review.

---

# 160. Access Settings

```text
Public
Login required
```

Future:

```text
Password protected
Signed link
```

---

# 161. Submission Settings

```text
Allow incomplete
Save progress
File policy
Duplicate policy
```

---

# 162. Security Settings

```text
CAPTCHA
rate limit profile
allowed embed origins
```

---

# 163. Tracking Settings

```text
Capture UTM
Capture referrer
Emit parent event
Preserve UTM on redirect
```

---

# 164. Success Settings

Main editing happens in Success tab, but Settings chooses:

```text
Designed page
Redirect URL
```

---

# 165. Form Versions UI

Manage Form → Versions:

```text
Version 6    Live
Published Sep 17 11:30

Version 5
Published Sep 14

Version 4
...
```

Actions:

```text
View
Compare
Restore to Draft
```

Never mutate historical versions.

---

# 166. Version Comparison

Later/optional:

```text
Fields added
Fields removed
Mapping changed
Theme changed
Success page changed
```

Useful for admin confidence.

---

# 167. Templates

Not required by client, but architecture should allow future templates.

Examples:

```text
Lead Capture
Support Request
Event Registration
Feedback
Contact Request
```

Template should create a Draft copy.

---

# 168. Form Library / Reusable Sections

Future architecture opportunity:

```text
Saved field group
Saved section
```

Example:

```text
Address
  Street
  City
  Postal Code
  Country
```

Do not block v1 for this.

---

# 169. API Versioning

Use `v1` namespace from the beginning.

This allows future runtime changes without breaking old embed clients.

---

# 170. Public Schema Contract

Once published, preserve compatibility for that version.

If runtime format changes, compiler can emit:

```text
schema_version: 1
```

Example:

```json
{
  "schema_version": 1
}
```

---

# 171. Compatibility Layer

Create:

```text
forms_pro/compatibility/v16.py
```

Only for actual framework differences, not business logic.

Purpose:

- centralize v16-specific helpers,
- simplify future v17 port,
- avoid scattered version checks.

Avoid:

```python
if frappe.__version__.startswith("16")
```

throughout the codebase.

---

# 172. Phase Plan

---

## Phase 0 — Fork, Baseline, Reproduction

Deliver:

```text
fork
upstream remote
version-16 branch
baseline tag
clean v16 bench
current defect list
screenshots/logs
compatibility matrix
```

Exit:

```text
all current upstream failures reproduced or explicitly marked unable to reproduce
```

---

## Phase 1 — Frappe v16 Compatibility

Work:

```text
Python 3.14
Node 24
Ruff py314
Node type alignment
Frappe dependency pin
navigation
permissions
query APIs
sort behavior
Single values
POST semantics
translations
testing flags
production assets
hooks
team/invitation
```

Exit:

```text
clean install/build/migrate
basic builder/public form works
```

This phase is the **highest priority**.

---

## Phase 2 — Remove Destructive Target Mutation

Work:

```text
remove set_doctype_fields side effect
stop target schema changes
stop automatic target pollution
migration compatibility
regression tests
```

Exit:

```text
saving form cannot alter target metadata
```

---

## Phase 3 — Generic Form Schema & Mapping Engine

Work:

```text
field_key
source_type
mapping types
target capabilities
field compatibility registry
generic adapter
child tables
Links
files
server constants
```

Exit:

```text
same engine works on multiple unrelated DocTypes
```

---

## Phase 4 — Submission Architecture

Work:

```text
FP Form Submission
record strategies
processing service
target reference
fail/retry behavior
tracking metadata
```

Exit:

```text
submission history independent from target document
```

---

## Phase 5 — Publishing / Versioning / Lifecycle

Work:

```text
Draft/Published/Archived
immutable versions
compiler
publish validation
restore/version UI
```

Exit:

```text
draft edits do not affect live version
```

---

## Phase 6 — Builder UX Enhancement

Work:

```text
new Studio navigation
field palette
target picker
mapping UI
conditions
undo/redo
autosave
warnings
responsive preview
```

Exit:

```text
normal business user can build without technical field editing
```

---

## Phase 7 — Success Page Designer

Work:

```text
Success tab
blocks
theme inheritance
responsive preview
merge tags
redirect mode
receipt integrity
```

Exit:

```text
client can visually build post-submit experience
```

---

## Phase 8 — Theme / Corporate Design

Work:

```text
theme tokens
theme editor
reusable themes
public CSS variables
success inheritance
```

Exit:

```text
corporate styling without CSS coding
```

---

## Phase 9 — Embed

Work:

```text
iframe runtime
embed.js
origin allowlist
CSP/frame policy
auto resize
events
copy embed UI
```

Exit:

```text
form works reliably on external test website
```

---

## Phase 10 — CAPTCHA & Security Hardening

Work:

```text
reCAPTCHA v3
rate limits
Guest API restriction
Link security
upload security
XSS sanitation
security tests
```

Exit:

```text
public threat checklist passes
```

Some baseline security fixes should happen earlier even if this phase contains final hardening.

---

## Phase 11 — Analytics & Tracking

Work:

```text
submission KPI
timeseries
date filter
sources
UTM
target created/updated
GA/GTM event
```

Exit:

```text
client can measure submissions and conversions
```

---

## Phase 12 — Migration / UAT / Production

Work:

```text
upgrade rehearsal
data audit
performance
UAT
bug fixing
backup
rollback
release notes
deployment guide
```

---

# 173. Recommended Ticket Breakdown

1. Fork Forms Pro and establish upstream baseline  
2. Create Frappe v16 compatibility matrix  
3. Align Python 3.14 / Ruff configuration  
4. Align Node 24 frontend environment  
5. Pin Forms Pro version-16 Frappe dependency  
6. Audit Frappe v16 navigation/app-screen integration  
7. Audit permission hooks for v16 semantics  
8. Audit Query Builder/get_list/get_all usage  
9. Fix implicit sort assumptions for v16  
10. Audit v16 Single DocType value casting  
11. Convert state-changing APIs to POST semantics  
12. Audit translation/test APIs removed/deprecated in v16  
13. Fix team/invitation v16 behavior  
14. Add clean-install and upgrade CI tests  
15. Restrict Guest DocType schema exposure  
16. Remove `set_doctype_fields()` automatic target mutation  
17. Stop automatic `fp_*` fields on target DocTypes  
18. Add stable Form Field keys  
19. Add generic mapping metadata  
20. Build target DocType capability inspector  
21. Build field capability registry  
22. Implement generic scalar mapping  
23. Implement server constant mapping  
24. Implement child table/repeating group mapping  
25. Secure Link field option API  
26. Implement secure file upload flow  
27. Create FP Form Submission  
28. Implement Create New strategy  
29. Implement Update Existing strategy  
30. Implement Create or Update strategy  
31. Implement Collect Submission Only strategy  
32. Add target adapter interface  
33. Add Draft/Published/Archived lifecycle  
34. Add immutable FP Form Version  
35. Build publishing compiler/validator  
36. Redesign Form Studio shell  
37. Improve target field picker  
38. Add form-only field mapping UX  
39. Add conditional logic UI  
40. Add autosave  
41. Add undo/redo  
42. Add responsive preview  
43. Build Success Page designer  
44. Add success blocks  
45. Add safe success merge variables  
46. Add redirect success mode  
47. Build theme token system  
48. Build visual Design tab  
49. Add reusable themes  
50. Implement standalone public runtime hardening  
51. Implement iframe embed runtime  
52. Implement embed.js  
53. Implement allowed embedding origins  
54. Implement iframe resize/postMessage events  
55. Add Copy Embed UI  
56. Implement Forms Pro Settings  
57. Implement reCAPTCHA v3  
58. Implement rate limiting  
59. Add public API security regression suite  
60. Add submission analytics  
61. Add UTM/referrer capture  
62. Add GA/GTM conversion event  
63. Build submission browser  
64. Build versions UI  
65. Add archive/restore UX  
66. Add duplicate form  
67. Write migration patches for existing forms  
68. Run production-data migration rehearsal  
69. Run client UAT  
70. Production release / rollback runbook

---

# 174. Release Milestones

## Milestone A — Frappe v16 Stable Fork

Must include:

```text
clean install
clean migrate
build
working SPA
working public route
working simple submission
security baseline
```

No new major client features until stable.

---

## Milestone B — Safe Generic Form Core

```text
non-destructive target behavior
generic mappings
multiple DocTypes
submission records
publishing/versioning
```

---

## Milestone C — Client Builder Experience

```text
enhanced Studio
custom labels
custom mapped fields
hidden defaults
conditional logic
files
preview
theme
success designer
```

---

## Milestone D — Website/Marketing Features

```text
embed
CAPTCHA
analytics
tracking
thank-you redirect
archive
```

---

## Milestone E — Production

```text
migration
UAT
security
performance
rollback
release
```

---

# 175. Definition of Done

A feature is complete only with:

```text
backend
frontend
permissions
validation
migration
tests
error handling
documentation
```

Public features additionally require:

```text
Guest security
rate limit
mobile test
embed test
abuse test
```

---

# 176. UAT Requirement Scenarios

## Custom label

Target field:

```text
System Type Interest
```

Form label:

```text
Where will the system be installed?
```

Expected:

```text
public form shows custom label
target DocType metadata unchanged
```

---

## Custom form field mapped to target

Create:

```text
form-only Select
```

Map to:

```text
an existing target field
```

Submit.

Expected mapped target value.

---

## Hidden value

Configure:

```text
language = German
hidden + locked
```

Manipulated browser sends another value.

Expected server uses German.

---

## Generic target

Repeat equivalent form tests against at least:

```text
one standard DocType
one custom DocType
one DocType with child table
```

No target-specific source code changes.

---

## Success design

Build:

```text
icon
heading
paragraph
CTA
```

Expected same appearance:

```text
preview
standalone
embedded
```

---

## Redirect

Successful submission redirects only after target processing succeeds.

---

## Publish version

Edit live form.

Expected:

```text
public remains old version until Publish
```

---

## Archive

Archive published form.

Expected:

```text
no new submissions
history remains
analytics remains
```

---

## CAPTCHA

Invalid token rejected.

Valid submission succeeds.

---

## Analytics

Known number of submissions in range returns correct count.

---

# 177. Security Release Checklist

```text
[ ] Guest cannot fetch arbitrary DocType schema
[ ] Guest cannot choose target DocType
[ ] Guest cannot choose target field
[ ] Guest cannot submit unknown field keys
[ ] hidden locked values cannot be overwritten
[ ] unpublished forms cannot submit
[ ] archived forms cannot submit
[ ] old invalid versions handled safely
[ ] public Links are allowlisted
[ ] Dynamic Link cannot enumerate arbitrary DocTypes
[ ] files validated
[ ] CAPTCHA verified server-side
[ ] rate limit enabled
[ ] rich text sanitized
[ ] success merge values escaped
[ ] iframe origins checked
[ ] postMessage origin checked
[ ] no PII sent to analytics event
[ ] no secret returned to client
[ ] no traceback returned to Guest
[ ] normal form save does not mutate target schema
```

---

# 178. Frappe v16 Release Checklist

```text
[ ] Python 3.14
[ ] Ruff py314
[ ] Node 24
[ ] @types/node aligned
[ ] Frappe pinned to v16
[ ] app screen works
[ ] SPA routes refresh correctly
[ ] permission hooks audited
[ ] get_list/get_all audited
[ ] default ordering audited
[ ] query builder behavior tested
[ ] Single values audited
[ ] POST semantics audited
[ ] translation APIs audited
[ ] frappe.in_test usage audited
[ ] hooks tested
[ ] invitation flow tested
[ ] production build tested
[ ] clean install tested
[ ] upgrade tested
```

---

# 179. Production Deployment

Before:

```text
database backup
file backup
record current git SHAs
migration rehearsal complete
rollback snapshot ready
```

Deploy:

```bash
bench --site <site> maintenance-mode on

# update app
# install exact locked dependencies

bench setup requirements
bench build --app forms_pro
bench --site <site> migrate
bench --site <site> clear-cache

bench --site <site> maintenance-mode off
```

Exact commands depend on infrastructure.

---

# 180. Rollback

Because migrations add schema/data:

```text
code rollback alone may not be sufficient
```

Safe full rollback:

```text
restore database
restore files if required
restore previous app commit
build/restart
```

Design migrations to be additive/non-destructive to minimize rollback risk.

---

# 181. Documentation to Ship

```text
README
INSTALL-V16.md
UPGRADE-V16.md
ARCHITECTURE.md
PUBLIC-API.md
EMBEDDING.md
SECURITY.md
FORM-MAPPING.md
THEMES.md
SUCCESS-PAGES.md
MIGRATION.md
TESTING.md
RELEASE.md
```

---

# 182. Architecture Decision Records

Create:

```text
docs/adr/
```

## ADR-001
Fork Forms Pro instead of rebuilding.

## ADR-002
Remain Vue 3/Frappe UI.

## ADR-003
Support Frappe v16 first.

## ADR-004
Do not mutate target DocType schema.

## ADR-005
Use stable field keys.

## ADR-006
Use immutable published versions.

## ADR-007
Keep submissions separate from target records.

## ADR-008
Use generic target adapters.

## ADR-009
Use iframe-based embed.

## ADR-010
Success page is first-class schema.

## ADR-011
Public client never controls target metadata.

---

# 183. Scope We Should Avoid Initially

Do not block first production release on:

```text
AI form generation
full workflow builder
arbitrary server scripts
arbitrary JS transforms
payment collection
electronic signatures
complex calculations
advanced funnel analytics
A/B testing
webhook automation system
multi-language editor
```

Architect for extension, but ship required functionality first.

---

# 184. Future Extensions

The architecture can later support:

```text
form templates
section library
multi-language labels
webhooks
workflow actions
email notifications
CRM automations
A/B variants
field-level analytics
abandonment tracking
form scoring
spam provider abstraction
Cloudflare Turnstile
hCaptcha
custom domains
```

---

# 185. Final Engineering Principles

## Principle 1

**Frappe v16 compatibility before feature expansion.**

---

## Principle 2

**A form is not a DocType schema editor.**

---

## Principle 3

**Target DocTypes remain clean and independent.**

---

## Principle 4

**Published forms are immutable versions.**

---

## Principle 5

**Public clients submit field keys, never target metadata.**

---

## Principle 6

**The target engine is generic.**

Special adapters are exceptions, not the architecture.

---

## Principle 7

**The builder and runtime are separate concerns.**

The builder can evolve without breaking published forms.

---

## Principle 8

**Success experience is part of the form product.**

It gets its own designer, schema, preview and versioning.

---

## Principle 9

**Security is enforced server-side.**

Browser validation is only UX.

---

## Principle 10

**Ease of use is a product requirement.**

Users should build forms visually without understanding Frappe internals.

---

# 186. Recommended Immediate Execution Order

```text
01  Fork + baseline tag
02  Build clean Frappe v16 environment
03  Reproduce current v16 problems
04  Fix Python 3.14 / Node 24 / dependency alignment
05  Audit navigation, permissions, queries, hooks and API semantics
06  Pass clean v16 install/build/migrate gate
07  Close Guest schema-exposure issue
08  Remove target DocType schema mutation
09  Stop injecting Forms Pro fields into target DocTypes
10  Add stable field keys
11  Add generic mapping engine
12  Add target capability inspector
13  Add FP Form Submission
14  Add generic record strategies
15  Add immutable versions
16  Add Draft/Published/Archived
17  Refine Form Studio UX
18  Add child-table and Link/file hardening
19  Build Success Page designer
20  Build theme designer
21  Build iframe/embed.js
22  Add CAPTCHA and final security hardening
23  Add analytics/tracking
24  Migrate existing forms
25  Full E2E/UAT
26  Production rollout
```

This order minimizes rework.

---

# 187. Product Success Criteria

The release is successful when a Forms Pro Manager on Frappe v16 can:

1. create a new form,
2. select an eligible standard or custom target DocType,
3. browse target fields safely,
4. drag them onto the canvas,
5. change form labels without touching DocType metadata,
6. add form-only fields,
7. map them to target fields,
8. add hidden/server preset values,
9. configure required fields,
10. use common Frappe field types,
11. use child-table repeating sections where supported,
12. create multi-page forms,
13. add conditions without JSON editing,
14. upload files securely,
15. style the form visually,
16. design a success page visually,
17. preview both form and success page responsively,
18. publish an immutable version,
19. use the standalone URL,
20. copy an embed snippet,
21. submit from an external website,
22. pass invisible CAPTCHA,
23. create/update the intended target record,
24. retain an independent FP Submission,
25. track submissions by date,
26. emit GA/GTM-friendly events,
27. archive and restore forms,
28. maintain historical submissions and versions,
29. operate without adding Forms Pro fields to target DocTypes,
30. operate reliably on Frappe/ERPNext v16.

---

# 188. Research References

## Forms Pro

Repository:

https://github.com/bwhtech/forms_pro

Architecture notes:

https://github.com/bwhtech/forms_pro/blob/develop/CLAUDE.md

Python/Frappe dependency configuration:

https://github.com/bwhtech/forms_pro/blob/develop/pyproject.toml

Form controller and current linked DocType mutation:

https://github.com/bwhtech/forms_pro/blob/develop/forms_pro/forms_pro/doctype/form/form.py

Form schema:

https://github.com/bwhtech/forms_pro/blob/develop/forms_pro/forms_pro/doctype/form/form.json

Form Field schema:

https://github.com/bwhtech/forms_pro/blob/develop/forms_pro/forms_pro/doctype/form_field/form_field.json

Form Field controller/type mapping:

https://github.com/bwhtech/forms_pro/blob/develop/forms_pro/forms_pro/doctype/form_field/form_field.py

Frontend package versions:

https://github.com/bwhtech/forms_pro/blob/develop/frontend/package.json

Form Generator / target-field injection:

https://github.com/bwhtech/forms_pro/blob/develop/forms_pro/utils/form_generator.py

External embedding issue:

https://github.com/bwhtech/forms_pro/issues/53

Guest DocType schema exposure issue:

https://github.com/bwhtech/forms_pro/issues/76

---

## Frappe v16

Migration guide:

https://github.com/frappe/frappe/wiki/Migrating-to-version-16

Frappe hooks/navigation reference:

https://github.com/frappe/frappe/blob/develop/hooks.md

Frappe Web Form implementation reference:

https://github.com/frappe/frappe/blob/develop/frappe/website/doctype/web_form/web_form.py

Frappe Web Form template/success-page reference:

https://github.com/frappe/frappe/blob/develop/frappe/website/doctype/web_form/templates/web_form.html

---

# 189. Final Recommendation

Proceed with the fork, but treat it as a product-level refactor rather than a collection of patches.

The fork should become:

```text
Frappe v16-compatible Forms Pro
            +
generic DocType mapping engine
            +
safe public submission platform
            +
visual Form Studio
            +
visual Success Page Studio
            +
website embedding
            +
security
            +
analytics
```

The **first milestone must be v16 stability**.

The **second milestone must be eliminating destructive target DocType behavior**.

Only after those two foundations are correct should the project invest heavily in design, embed, success pages and analytics.

That sequence creates a maintainable general-purpose form platform instead of a form builder that only works for one DocType or one current Frappe patch version.
