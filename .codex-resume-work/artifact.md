# Resume template execution contract

## Reference

- Path: `D:\company_agent\.codex-resume-work\source.docx`
- SHA-256: `F9AFD7DC9B543B68DDF0ABDDF4CB6C78E2CDABD07B19214A2403C0F944F4CB76`
- Page count: 1 (verified through Microsoft Word PDF export and 144-DPI PNG render)
- Section count: 1
- Render evidence: `D:\company_agent\.codex-resume-work\source-page-1.png`
- Style evidence: `D:\company_agent\.codex-resume-work\template-style-evidence.json`

## Page system

- A4 portrait, 8.27 x 11.69 in.
- Margins: left 0.53 in, right 0.53 in, top 0.45 in, bottom 0.41 in.
- One section; no first-page or odd/even header variant.
- Footer is independent and contains a centered candidate/role label.
- Required output remains one page.

## Typography and components

- Visual system: white page, restrained dark blue (`#1F4E79`) section headings and thin blue rules.
- Name: bold dark blue, approximately 22 pt in the editable header table's left cell.
- Contact and target lines: gray, approximately 9-10 pt.
- Section headings: 11 pt bold dark blue, single spacing, 5 pt before and 2 pt after.
- Project headings: bold dark text, approximately 11 pt, compact spacing.
- Project details: real `List Bullet` paragraphs, approximately 9-10 pt, compact line spacing.
- Body text: dark gray/black, approximately 9-10 pt.
- Header table: one row, two columns; left text width 5,327,650 EMU, right image width 1,079,500 EMU.
- Portrait image: `word/media/image1.jpg`, inline, 1.04 x 1.56 in; preserve unchanged.
- Skills table: four rows, two columns; widths 863,600 and 5,543,550 EMU; blue label cells and text-only detail cells.
- Footer: centered muted text, approximately 8 pt.

## Content flow and slot map

1. `word/document.xml`, first table, left cell: candidate name, contact line, target-role line. Rewrite role only; preserve contact data.
2. `word/document.xml`, first table, right cell: portrait. Preserve relationship and media unchanged.
3. Body paragraphs 0-1: education heading and education line. Preserve facts.
4. Body paragraphs 2-12: project heading plus two project blocks. Rewrite project titles/details for product-role positioning; keep four bullets per project and one-page capacity.
5. Body paragraphs 13-14 plus second table: skills heading and four skill rows. Rewrite labels/details for product roles while preserving 4x2 geometry.
6. Body paragraph 14-15: self-evaluation heading and one compact evidence-based paragraph.
7. `word/footer1.xml`: candidate and target-role label. Rewrite role only.

## Package preservation

- Editable: `word/document.xml`, `word/footer1.xml`.
- Preserve-only: `[Content_Types].xml`, `_rels/.rels`, all `customXml/*`, `docProps/*`, `word/_rels/document.xml.rels`, `word/endnotes.xml`, `word/fontTable.xml`, `word/footnotes.xml`, `word/media/image1.jpg`, `word/numbering.xml`, `word/settings.xml`, `word/styles.xml`, `word/theme/theme1.xml`, `word/webSettings.xml`.
- Key preserve-only hashes: image `f942fe8145da3c251523736fd4d4e83617a4b2485aaa2d7ba17145e356a9c0f1`; numbering `febc4346d5f383c1286fa5fc84353c6e0cbdfb1f952996edcfc932a4beb4f24d`; styles `6142df29fc4ee9229da6bfdb3541ae9467c9c0d4b446168fbedee2eb25dc2676`; theme `b2295d3198893d2c03f5e584c749a15751b798aefdcd9bee2889f13903d68cb2`.
- No fields, content controls, comments, headers, or additional images were found.

## Fidelity gates

- Retained source must remain byte-for-byte unchanged.
- Final output must preserve the original portrait, page geometry, section rules, two-column header, skills-table layout, and centered footer.
- Content must remain on one page with no clipping, overlap, broken bullets, or compressed table text.
- Product claims must be traceable to the user's actual projects; do not invent product metrics, users, internship experience, prototyping software, or formal PRD ownership.
