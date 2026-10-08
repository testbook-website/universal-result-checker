/**
 * Universal Result Checker - Google Sheets Webhook (Writes directly starting from Row 2)
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
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheets()[0];

    // Ensure header row exists at Row 1
    if (sheet.getRange("A1").getValue() === "") {
      sheet.getRange(1, 1, 1, 7).setValues([[
        "Timestamp",
        "Exam Name",
        "Tier / Zone",
        "Roll Number",
        "Candidate Name",
        "Mobile Number",
        "Status"
      ]]);
      sheet.getRange("A1:G1").setFontWeight("bold").setBackground("#e8f0fe");
    }

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

    // Find the first genuinely empty row in Column A (fills row 2, 3, 4 without skipping)
    var colA = sheet.getRange("A1:A").getValues();
    var nextRow = 2;
    for (var i = 1; i < colA.length; i++) {
      if (colA[i][0] !== "" && colA[i][0] !== null && colA[i][0] !== undefined) {
        nextRow = i + 2;
      }
    }

    var rowData = [
      timestamp,
      examName,
      tier,
      rollNumber,
      name,
      mobile,
      status
    ];

    // Write directly into row 2, 3, 4 etc.
    sheet.getRange(nextRow, 1, 1, rowData.length).setValues([rowData]);

    SpreadsheetApp.flush();

    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      message: "Data logged successfully",
      writtenAtRow: nextRow,
      sheetTitle: ss.getName(),
      sheetTab: sheet.getName(),
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
