Inhouse Development for EOL Application for TPMS Pairing & Diagnostics Execution	

Prepared by
SRI SAKTHIVEL R	

Table of Contents
S.NO	CONTENTS	PAGE NO
1	INTRODUCTION	
2	OPERATIONS	
2.1	TEST CASES	
2.1.1	API CALL	
2.1.2	WRITE_TPMS_FRONT	
2.1.3	WRITE_TPMS_REAR	
2.2	EXECUTION STEPS	
2.2.1	INITIATE PROCESS	
2.2.2	MONITOR TEST	
2.2.3	TEST COMPLETION & RESET PROCESS	
3	LOG VALIDATION	
3.1	FILE LOCATION	
3.2	FILE STRUCTURE	
3.3	OVERVIEW OF LOGS	
3.4	AUTO-DELETION OF LOGS	
4	SOFTWARE UPDATES	

1. INTRODUCTION
TVS NIRIX V1.3 is a dedicated desktop application developed for the validation of the Tire Pressure Monitoring System (TPMS) parameters in vehicles. The tool automates sensor pairing by interfacing with the cluster ECU, using the Vehicle Identification Number (VIN) as input. The software retrieves MAC IDs through an API, writes them to the cluster, and confirms the successful pairing. All operations are logged locally for traceability.

2. OPERATION
2.1 TEST CASES
   
2.1.1 API CALL
	Purpose: Initiates an API request to retrieve TPMS parameters (e.g., front and rear MAC addresses) for the entered VIN.
	Input: VIN number
	Output: Sets front_mac and rear_mac variables if successful; otherwise, returns False.
	Duration: Approximately 1 second (with a 1-second delay between tests).
	Success Criteria: Valid MAC addresses are retrieved and stored.
	Failure: Occurs if the API (http://10.121.2.107:3000/vehicles/processParams/VIN ) is unreachable or returns an error.

2.1.2 WRITE_TPMS_FRONT
	Purpose: Writes the front wheel MAC address to the TPMS system.
	Input: front_mac retrieved from API_CALL.
	Output: Returns True if the write operation succeeds, False otherwise.
	Duration: Approximately 1 second.
	Success Criteria: The TPMS system acknowledges the write operation.
	Failure: Occurs if front_mac is invalid or the write operation fails.

2.1.3 WRITE_TPMS_REAR
	Purpose: Writes the rear wheel MAC address to the TPMS system.
	Input: rear_mac retrieved from API_CALL.
	Output: Returns True if the write operation succeeds, False otherwise.
	Duration: Approximately 1 second.
	Success Criteria: The TPMS system acknowledges the write operation,
	Failure: Occurs if rear_mac is invalid or the write operation fails.

2.2	Execution Steps
2.2.1 Initiate Process: 
	Manually type a 17-character VIN starting with "MD6" (e.g., "MD612345678912345") in the "Enter VIN Number" field or use the scanner (Section 7) to input the VIN automatically.
 

2.2.2	Monitor Progress: 
	You have selected EJO mode. Please ensure that the scanned or entered VIN and the selected API (PRD/EJO). If they are not, an error message will appear in the instruction box stating that “Test Sequence Failed Please Check”.

	If any of the test sequences in this models fail, the relevant result box will show the red color which indicates the fail related to that test. The test sequence stops instantly if it fails, and the program resets after 15 seconds to enable a new VIN scan and resume the validation procedure.
 
2.2.3 Test Completion & Reset Process: 
	'All tests passed successfully!' will appear in the result box for once all test cases have been successfully completed. This notification will automatically disappear after ten seconds, enabling the operator to go on to the following validation cycle.
 

	The application clears the VIN input, resets the progress bar, and prepares for the next test cycle automatically with the given timeout.
3. Log Validation
3.1 File Location:
	Directory: D:\Python\TVS NIRIX\Modular App\ test_results
	Filename Format: <VIN>_<YYYYMMDD_HHMMSS>.txt 
3.2 File Structure:
VIN NUMBER: MD612345678912345
REAR WHEEL MAC: 00:11:22: 33:44:55
FRONT WHEEL MAC: 00:11:22: 33:44:66
TEST STATUS: OK
DATE: 2025-06-24 17:02:00
API REQUEST: http://10.121.2.107:3000/vehicles/flashFile/prd/MD629120000000000
API RESPONSE:
 

[2025-08-09 12:15:45.680] 
[2025-08-09 12:15:45.680] API_CALL: PASSED
[2025-08-09 12:15:45.680] TEST SEQUENCE: WRITE TPMS FRONT
[2025-08-09 12:15:45.680] Tx 07F3 8 01 C0 63 80 91 DD DD 00
[2025-08-09 12:15:45.680] Rx 07F1 8 01 C0 63 80 91 DD DD 55
[2025-08-09 12:15:45.680] Front MAC Write: PASSED
[2025-08-09 12:15:45.680] TEST SEQUENCE: WRITE TPMS REAR
[2025-08-09 12:15:45.680] Tx 07F3 8 01 C0 63 80 91 00 00 00
[2025-08-09 12:15:45.680] Rx 07F1 8 01 C0 63 80 91 00 00 55
[2025-08-09 12:15:45.680] Rear MAC Write: PASSED

3.3	Overview Of Logs
3.3.1	Header Information:
	VIN Number: MD629120000000000 – A 17-character identifier starting with "MD6", matching the required format and confirming it as the tested vehicle. 
	Test Status: OK – Indicates all tests passed successfully with no failures. 
	Date: 2025-08-09 12:15:45 – Timestamp of log generation, consistent with the test execution. 
	API Request: http://10.121.2.107:3000/vehicles/flashFile/prd/MD629120000000000 – Endpoint used with "prd" mode, matching the VIN's production context. 
	API Response: 
•	Status Code: 100 – Success code. 
•	Error Message: "" – No errors reported. 
•	data: Contains modules (VCU and IPC) with configurations.
3.3.2	Test Sequence:
	Test Sequence Name: Name of the specific test.
	Tx CAN ID: Input (Request), Rx ID: Output (Received can message)
	Status: Displays Passed or Failed.


3.4	Auto Deletion of Logs:

	Execution: Runs at startup, scanning for .txt files, sorting by modification time, and deleting them as needed to manage storage with the separate sub program log_cleanup.py
	Log Visibility: Cleanup actions may appear in console output, not test logs. Check the log folder to confirm only recent files remain, and review log_cleanup.py for specific criteria like max_age_days or max_files.

4.Software Updates:
4.1 TVS NIRIX V1.3
	Accepts manual VIN input or serial scanner input. Validates format and uniqueness.
	Fetch MAC addresses (Front & Rear) using VIN from a REST API. Send test result logs (VIN, MAC, status) to API endpoint. Handles authentication, retries, and failure handling.
	Save each test result with timestamp, VIN, MAC, and test status. Supports CSV, TXT, or JSON log formats. Automatic daily log deletion within the retention days.
