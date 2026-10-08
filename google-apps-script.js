/**
 * Universal Result Checker - Google Sheets Webhook
 * 
 * Instructions:
 * 1. Open your Google Sheet (Universal Result Checker Leads):
 *    https://docs.google.com/spreadsheets/d/1R06Ix6TG2O8NbZCbclCdSfdXCD-af0P3AEKMNChXLo8/edit
 * 2. Click "Extensions" > "Apps Script".
 * 3. Replace all code with this script and click Save (Floppy disk icon).
 * 4. Click "Deploy" > "Manage deployments".
 * 5. Click the Edit (pencil) icon:
 *    - Version: "New version"
 *    - Execute as: "Me"
 *    - Who has access: "Anyone"
 * 6. Click "Deploy".
 * 7. COPY THE WEB APP URL (ends with /exec).
 * 8. Paste that new URL into Render under APPS_SCRIPT_DEPLOYMENT_ID.
 */

function doGet(e) {
  return handleRequest(e);
}

function doPost(e) {
  return handleRequest(e);
}

function handleRequest(e) {
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(30000);
  } catch (lockErr) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: "Server busy: lock timeout"
    })).setMimeType(ContentService.MimeType.JSON);
  }

  try {
    // Automatically uses THIS spreadsheet
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheets()[0];

    // Parse incoming parameters
    var params = {};
    if (e && e.postData && e.postData.contents) {
      try {
        params = JSON.parse(e.postData.contents);
      } catch (err) {
        params = e.parameter || {};
      }
    } else if (e && e.parameter) {
      params = e.parameter;
    }

    var timestamp = Utilities.formatDate(new Date(), "Asia/Kolkata", "yyyy-MM-dd HH:mm:ss");
    var examName = String(params.exam_name || params.exam || params.Exam || "N/A").trim();
    var tier = String(params.tier || params.zone || params.Tier || "").trim();
    var rollNumber = String(params.rollNumber || params.roll_number || params.roll || params.Roll || "N/A").trim();
    var name = String(params.name || params.student_name || params.Name || "N/A").trim();
    var mobile = String(params.mobile || params.mobile_number || params.phone || "N/A").trim();
    var status = String(params.status || params.Status || "N/A").trim();

    // Append to sheet
    sheet.appendRow([
      timestamp,
      examName,
      tier,
      rollNumber,
      name,
      mobile,
      status
    ]);

    SpreadsheetApp.flush();

    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      message: "Data logged successfully",
      sheetTitle: ss.getName(),
      sheetTab: sheet.getName(),
      spreadsheetUrl: ss.getUrl(),
      timestamp: timestamp
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  } finally {
    try {
      lock.releaseLock();
    } catch (ignore) {}
  }
}
