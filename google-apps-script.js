/**
 * Universal Result Checker - Bound to Spreadsheet
 * Sheet ID: 1R06Ix6TG2O8NbZCbclCdSfdXCD-af0P3AEKMNChXLo8
 */

// Target Sheet ID explicitly
var TARGET_SHEET_ID = "1R06Ix6TG2O8NbZCbclCdSfdXCD-af0P3AEKMNChXLo8";

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
    var ss;
    try {
      ss = SpreadsheetApp.openById(TARGET_SHEET_ID);
    } catch (openErr) {
      ss = SpreadsheetApp.getActiveSpreadsheet();
    }
    
    var sheet = ss.getSheets()[0];

    // Parse parameters
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

    // Append entry directly
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
      sheetName: sheet.getName(),
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
