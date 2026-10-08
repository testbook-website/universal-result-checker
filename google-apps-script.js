/**
 * Universal Result Checker - High Concurrency Google Sheets Webhook
 * 
 * Instructions:
 * 1. Open Google Sheet: https://docs.google.com/spreadsheets/d/1R06Ix6TG2O8NbZCbclCdSfdXCD-af0P3AEKMNChXLo8/edit
 * 2. Click Extensions > Apps Script.
 * 3. Replace all code with this script.
 * 4. Click Save (Disk icon).
 * 5. Click Deploy > Manage deployments > Edit (pencil icon) > Version: "New version" > Deploy.
 */

function doGet(e) {
  return handleRequest(e);
}

function doPost(e) {
  return handleRequest(e);
}

function handleRequest(e) {
  var lock = LockService.getScriptLock();
  // Wait up to 30s to queue up burst traffic smoothly without dropping requests
  try {
    lock.waitLock(30000);
  } catch (lockErr) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: "Server busy: lock timeout"
    })).setMimeType(ContentService.MimeType.JSON);
  }

  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheets()[0];

    // Auto-create headers if sheet is completely empty
    if (sheet.getLastRow() === 0) {
      sheet.appendRow([
        "Timestamp",
        "Exam Name",
        "Tier / Zone",
        "Roll Number",
        "Candidate Name",
        "Mobile Number",
        "Status"
      ]);
      sheet.getRange("A1:G1").setFontWeight("bold").setBackground("#e8f0fe");
    }

    // Parse parameters from POST body or GET query params
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

    // Fast append
    sheet.appendRow([
      timestamp,
      examName,
      tier,
      rollNumber,
      name,
      mobile,
      status
    ]);

    // Force flush to ensure immediate writing
    SpreadsheetApp.flush();

    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      message: "Data logged successfully",
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
