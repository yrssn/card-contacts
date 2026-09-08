// 金山文档 AirScript（表格）—— 名片快查同步脚本
// 列结构：A 序 | B 语种 | C 大类 | D 名字 | E 性别 | F 备注 | G 职位 | H 主营业务关键词 | I 主营产品/服务类型
//         J 公司名 | K 官网 | L 邮箱 | M 电话 | N 正面照片 | O 反面照片 | P 导入人
// 支持的 action：health / list_sheets / ensure_sheet / add

const HEADERS = [
  "序", "语种", "大类", "名字", "性别", "备注", "职位", "主营业务关键词", "主营产品/服务类型",
  "公司名", "官网", "邮箱", "电话", "正面照片", "反面照片", "导入人",
];
const LAST_COL = "P";
const IMPORTER_COL = "P";

function text(value) {
  return value == null ? "" : String(value).trim();
}

function normalized(value) {
  return text(value).toLowerCase().replace(/[\s\-()（）+]/g, "");
}

function parsePayload() {
  let payload = Context.argv || {};
  if (payload.body != null) payload = payload.body;
  if (typeof payload === "string") payload = JSON.parse(payload);
  return payload || {};
}

function findSheet(name) {
  const wanted = text(name);
  const count = Application.Sheets.Count;
  for (let i = 1; i <= count; i += 1) {
    const sheet = Application.Sheets.Item(i);
    if (text(sheet.Name) === wanted) return sheet;
  }
  return null;
}

function listSheets() {
  const names = [];
  const count = Application.Sheets.Count;
  for (let i = 1; i <= count; i += 1) names.push(text(Application.Sheets.Item(i).Name));
  return names;
}

function writeHeaders(sheet) {
  sheet.Range(`A1:${LAST_COL}1`).Value2 = [HEADERS];
  sheet.Range(`A1:${LAST_COL}1`).Font.Bold = true;
}

function ensureSheet(name) {
  const wanted = text(name);
  if (!wanted) return { ok: false, error: "工作表名不能为空" };
  let sheet = findSheet(wanted);
  let created = false;
  if (!sheet) {
    const last = Application.Sheets.Item(Application.Sheets.Count);
    sheet = Application.Sheets.Add(null, last);
    sheet.Name = wanted;
    created = true;
  }
  const firstCell = text(sheet.Range("A1").Value2);
  if (!firstCell) writeHeaders(sheet);
  if (text(sheet.Range(`${IMPORTER_COL}1`).Value2) === "") sheet.Range(`${IMPORTER_COL}1`).Value2 = "导入人";
  return { ok: true, created, sheet: wanted, sheets: listSheets() };
}

function lastDataRow(sheet) {
  const used = sheet.UsedRange;
  return Math.max(1, used ? used.Row + used.Rows.Count - 1 : 1);
}

function rowIsEmpty(values) {
  for (let i = 0; i < Math.min(values.length, 13); i += 1) {
    if (text(values[i])) return false;
  }
  return true;
}

function compactRows(sheet) {
  for (let row = lastDataRow(sheet); row >= 2; row -= 1) {
    const values = sheet.Range(`A${row}:M${row}`).Value2[0] || [];
    if (rowIsEmpty(values)) sheet.Rows.Item(row).Delete();
  }
}

function findDuplicate(sheet, card) {
  const wantedName = normalized(card.name);
  const wantedCompany = normalized(card.company);
  const wantedPhone = normalized(card.phone);
  const wantedEmail = normalized(card.email);
  const end = lastDataRow(sheet);
  if (end < 2) return 0;
  const rows = sheet.Range(`A2:${LAST_COL}${end}`).Value2 || [];
  for (let index = 0; index < rows.length; index += 1) {
    const row = rows[index];
    const sameEmail = wantedEmail && normalized(row[11]) === wantedEmail;
    const samePhone = wantedPhone && normalized(row[12]) === wantedPhone;
    const samePerson = wantedName && wantedCompany && normalized(row[3]) === wantedName && normalized(row[9]) === wantedCompany;
    if (sameEmail || samePhone || samePerson) return index + 2;
  }
  return 0;
}

function setImageCell(sheet, address, url) {
  const cell = sheet.Range(address);
  if (!text(url)) return false;
  cell.ClearContents();
  const shape = sheet.Shapes.AddPicture(
    text(url),
    0,
    0,
    cell.Left + 2,
    cell.Top + 2,
    Math.max(40, cell.Width - 4),
    Math.max(40, cell.Height - 4),
  );
  if (!shape) throw new Error("金山文档没有返回图片对象");
  try { shape.Placement = 1; } catch (_) {}
  return true;
}

function configurePhotoCells(sheet, row) {
  sheet.Range(`N${row}:O${row}`).RowHeight = 86;
  sheet.Range("N:N").ColumnWidth = 18;
  sheet.Range("O:O").ColumnWidth = 18;
}

function addContact(payload) {
  const sheetName = text(payload.sheetName);
  if (!sheetName) return { ok: false, error: "缺少工作表名 sheetName" };
  const ensured = ensureSheet(sheetName);
  if (!ensured.ok) return ensured;
  const sheet = findSheet(sheetName);
  compactRows(sheet);
  const card = payload.card || {};
  let row = findDuplicate(sheet, card);
  const duplicate = row > 0;
  if (!row) row = Math.max(2, lastDataRow(sheet) + 1);
  if (!duplicate) {
    const previousNumber = row > 2 ? Number(sheet.Range(`A${row - 1}`).Value2) || row - 2 : 0;
    const values = [[
      previousNumber + 1,
      text(card.language),
      text(payload.moduleLabel),
      text(card.name),
      text(card.sex),
      text(card.note),
      text(card.department),
      text(card.businessKeywords).slice(0, 10),
      text(card.productServiceType).slice(0, 10),
      text(card.company),
      text(card.website),
      text(card.email),
      text(card.phone),
    ]];
    sheet.Range(`A${row}:M${row}`).Value2 = values;
  }
  if (text(payload.importer)) sheet.Range(`${IMPORTER_COL}${row}`).Value2 = text(payload.importer);
  if (text(payload.frontImageUrl) || text(payload.backImageUrl)) configurePhotoCells(sheet, row);
  const frontAdded = setImageCell(sheet, `N${row}`, payload.frontImageUrl);
  const backAdded = setImageCell(sheet, `O${row}`, payload.backImageUrl);
  const values = sheet.Range(`A${row}:${LAST_COL}${row}`).Value2[0] || [];
  return {
    ok: true,
    duplicate,
    row,
    sheet: sheetName,
    values,
    images: { front: frontAdded, back: backAdded },
  };
}

function main() {
  try {
    const payload = parsePayload();
    if (payload.action === "add") return addContact(payload);
    if (payload.action === "ensure_sheet") return ensureSheet(payload.sheetName);
    if (payload.action === "list_sheets") return { ok: true, sheets: listSheets() };
    if (payload.action === "health") return { ok: true, version: "card-contacts-v1", sheets: listSheets() };
    return { ok: false, error: "不支持的操作" };
  } catch (error) {
    return { ok: false, error: String(error && error.message ? error.message : error) };
  }
}

return main();
