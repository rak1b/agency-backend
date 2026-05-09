# Frontend integration: Hanseo PDF + extended `StudentFile` fields

Short guide for **Next.js** (or any web client) consuming the Agency backend after the Hanseo / student-file changes.

Base URL examples below use:

`{API_BASE}` = your backend origin + `/api/v1/agency-management/web`  
(e.g. `https://api.example.com/api/v1/agency-management/web`)

All endpoints require the **same auth** you already use (e.g. `Authorization: Bearer <token>`), unless noted as public.

---

## 1. Student file: new & updated fields

These live on the **`StudentFile`** resource (list/detail/create/update responses and payloads).

| Field | Type | Notes |
|--------|------|--------|
| `gender` | string | One of: `MALE`, `FEMALE`, `OTHER` (default `OTHER`). |
| `nationality` | string | Optional. |
| `place_of_birth` | string | Optional. |
| `present_address` | string | Optional; can be long text. |
| `permanent_address` | string | Optional. |
| `education_background` | `array` \| `null` | JSON list of education rows (see shape below). |
| `family_particulars` | `array` \| `null` | JSON list of family rows (see shape below). |
| `translator_profile` | `object` \| `null` | Optional; Hanseo translation page (see shape below). |
| `translated_documents_note` | string | Short line, e.g. `"APPLICANT NID, PARENTS NID"`. |
| `application_statement` | string | Page‑1 statement; PDF uses a default if empty. |
| `highest_education_postal_code` | string | Page‑2 footer. |
| `highest_education_address` | string | Page‑2 footer. |
| `highest_education_fax` | string | Page‑2 footer. |
| `highest_education_website` | string | Page‑2 footer. |

Existing fields unchanged: `student_file_id`, `slug`, `given_name`, `surname`, `middle_name`, `date_of_birth`, `passport_number`, `passport_photo_url`, `phone_whatsapp`, `email`, `father_name`, `mother_name`, etc.

### `education_background` — suggested row shape

Up to **3** rows are typical (elementary / college / university). Extra properties are ignored.

```json
{
  "degree": "College",
  "institution": "Example High School and College",
  "study_period": "2021-2023",
  "result": "GPA: 4.08",
  "graduation_date": "2023-11-26",
  "institution_phone": "+880…",
  "admission_date": "2021-11-12"
}
```

- **`admission_date`** / **`graduation_date`**: use `YYYY-MM-DD` when possible (Hanseo page 2).
- **`study_period`**: e.g. `2021-2023` fills the “from … to …” sentence when full dates are missing.

### `family_particulars` — suggested row shape

```json
{
  "relation": "FATHER",
  "name": "…",
  "date_of_birth": "1975-02-01",
  "occupation": "…",
  "monthly_income": "…",
  "workplace": "…",
  "workplace_phone": "+880…"
}
```

If this array is empty, the PDF can still show **father/mother** from `father_name` / `mother_name` only.

### `translator_profile` — optional object

```json
{
  "nationality": "Bangladeshi",
  "name": "…",
  "date_of_birth": "1999-08-05",
  "gender": "MALE",
  "address": "Multi-line\naddress",
  "home_phone": "…",
  "mobile": "…"
}
```

`gender` may be `MALE` / `FEMALE` or `M` / `F`.

---

## 2. CRUD: student files (authenticated)

- **List / create:** `GET` / `POST` `{API_BASE}/student-files/`
- **Detail / update:** `GET` / `PATCH` / `PUT` `{API_BASE}/student-files/{slug}/`

Send new fields in JSON body on **create** and **patch** like any other field. Types: JSON fields should be real JSON arrays/objects, not stringified JSON, unless your client already stringifies for multipart edge cases.

---

## 3. Public website submit (optional)

If the marketing site creates a file without staff login:

`POST {API_BASE}/public/student-files/submit/`

The serializer now accepts the **same optional fields** as above (`gender`, `nationality`, `education_background`, …) in addition to the existing required public payload (`given_name`, `surname`, `passport_number`, etc.).

---

## 4. Hanseo PDF download (authenticated)

**Endpoint:** `GET {API_BASE}/university-form-download/`

**Auth:** Required (`IsAuthenticated`). Same token as other agency-management routes.

**Query (provide one of):**

| Query param | Example | Description |
|-------------|---------|-------------|
| `student_file_id` | `STF12345678` | Preferred public id from the student file. |
| `slug` | file slug | Alternate lookup. |
| `id` | `42` | Numeric database id. |

**Example:**

```http
GET /api/v1/agency-management/web/university-form-download/?student_file_id=STF12345678
Authorization: Bearer <access_token>
```

**Responses:**

- `200` — `Content-Type: application/pdf`; `Content-Disposition: attachment; filename="hanseo-application-<id>.pdf"`.
- `400` — missing all of `student_file_id`, `slug`, and `id`.
- `401` — not authenticated.
- `404` — file not found or not visible for this user (tenant / student portal rules).

### Next.js: trigger browser download

Use `fetch` with auth header, read as **blob**, then create an object URL (or FileSaver pattern):

```ts
async function downloadHanseoPdf(accessToken: string, studentFileId: string) {
  const url = `${process.env.NEXT_PUBLIC_API_BASE}/api/v1/agency-management/web/university-form-download/?student_file_id=${encodeURIComponent(studentFileId)}`;
  const res = await fetch(url, {
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}` },
    credentials: "include", // only if you use cookies instead of Bearer
  });
  if (!res.ok) throw new Error(await res.text());
  const blob = await res.blob();
  const cd = res.headers.get("Content-Disposition") ?? "";
  const match = /filename="([^"]+)"/.exec(cd);
  const filename = match?.[1] ?? `hanseo-${studentFileId}.pdf`;
  const href = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = href;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(href);
}
```

Adjust `NEXT_PUBLIC_API_BASE` to match your env (no trailing slash issues: keep query string as shown).

---

## 5. Behaviour / UX notes for frontend

1. **Show `student_file_id`** on student detail screens and use it for the PDF button (`?student_file_id=…`).
2. **Forms:** add inputs for gender, addresses, nationality, place of birth; optional structured editors (repeatable rows) for education and family JSON.
3. **PDF button:** disable or hide for users without a token; handle `404` with a clear message (“File not found or no access”).
4. **Breaking change:** this PDF route is **no longer anonymous**; do not call it without auth.

---

## 6. Quick checklist

- [ ] Student create/edit forms include new fields + validation (`gender` enum).
- [ ] JSON editors or repeatable sections for `education_background` / `family_particulars`.
- [ ] Optional translator + Hanseo extras for advanced flows.
- [ ] “Download Hanseo pack” uses `GET` + blob download + `student_file_id` query.
- [ ] Types / Zod schemas updated for `StudentFile` API responses.

If the OpenAPI schema is enabled in your environment, regenerate the client from `/api/schema/` after deploy for exact TypeScript types.
