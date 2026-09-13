GANAPATI CHASMA GHAR V2

Included: index.html, script.js, style.css, firebase.js, firestore.rules.

IMPORTANT: Enable Firebase Authentication -> Email/Password.
Create Firestore Database, then Firestore Database -> Rules and publish firestore.rules.

Records are stored at users/{Firebase UID}/patients/{patient ID}. Rules allow an authenticated user to read/write only that user's subcollection and deny all other paths.

Old records in the previous top-level patients collection are not automatically migrated.

Deploy the website via GitHub -> Vercel. Firebase rules must be published separately in Firebase Console.


Latest updates:
- Dashboard now has a clickable Patient Records tile.
- Patient Records is a separate dashboard section, not part of the patient entry form.
- Search is located inside Patient Records.
- BCVA now has its own ADD (RE/LE) and PD fields.
- PG now has its own separate ADD (RE/LE) and does not have PD.
- All example/placeholder text such as "e.g." has been removed from form inputs.
- Frame Details is now a manually fillable text field instead of a dropdown.
- Payment Details follows the requested 2-column layout: Frame Amt, Lens Amt, Medicines, Clinical Test, Others, Total, Advance, Remaining.
- Payment Total = Frame + Lens + Medicines + Clinical Test + Others; Remaining = Total - Advance.
- Payment amounts use 0.10 increments.
- Age boxes now have explicit "Year / Month / Days" labels above each box (instead of relying on placeholder text), and the Age column is wider so the boxes aren't squeezed down to spinner-only width.
- Previous Section navigation now moves backward through the form sections (1 to 8) and focuses the first field of the previous section. A top Back button and keyboard ArrowLeft/Alt+ArrowLeft navigation are also supported while the form is open.


Updated form changes:
- Age can be entered as Years, Months, and Days.
- Lens/Frame Right Eye and Left Eye SPH/CYL/AXIS/VA/ADD input boxes are wider.
- Added Previous Section button to move backward through the main form areas.
- Existing Firebase user-specific Firestore structure is preserved.

Latest UI updates:
- Clinical Details now labels the previous Diagnosis field as Treatment and adds a separate Diagnosis field beside it.
- Added logout confirmation dialog: “Do you really want to logout ?” with Yes and No actions.
- Refreshed the visual design with a more professional clinic interface, polished spacing, cards, navigation, focus states, and a custom vector eye-care logo mark.
- Existing Firebase authentication, Firestore user-specific records, age fields, refraction fields, payment calculations, patient records, search, edit/delete, and navigation are preserved.

SMS BROADCAST SETUP
-------------------
The new SMS Broadcast tab lets the clinic compose an SMS, insert emojis, select individual patients or all patients, and send to their stored phone numbers.

IMPORTANT: A normal browser cannot directly use a computer/phone SIM balance. For real carrier-SMS delivery, connect an Android phone containing the clinic SIM to an SMS gateway that exposes an HTTP API. The included Vercel API endpoint is configured for SMS Gateway for Android's API format. Their current documentation supports sending a text to multiple phone numbers and selecting a SIM number.

Vercel environment variables required:
SMS_GATE_URL=https://api.sms-gate.app/3rdparty/v1/messages
SMS_GATE_USERNAME=your_gateway_username
SMS_GATE_PASSWORD=your_gateway_password
SMS_GATE_DEVICE_ID=your_android_device_id
SMS_GATE_SIM_NUMBER=1

The Android phone must be online/active and have the desired SIM inserted. Carrier SMS balance/message-pack usage is handled by that SIM/carrier, subject to the carrier's own limits and policies. Do not put gateway credentials directly into index.html or script.js.

PHONE + SMS GATEWAY CONFIGURATION (CLOUD SERVER)
-------------------------------------------------
1. Use an Android phone with the clinic SIM inserted. The phone can still be used normally for calls, WhatsApp, etc.
2. Install SMS Gateway for Android on the Android phone.
3. Grant the app its required permissions, especially SEND_SMS. If you use SIM selection, also allow READ_PHONE_STATE.
4. Open the app and enable Cloud Server.
5. Tap the Offline/Online status control and connect the device. After the first successful connection, the app generates the Cloud Server username and password automatically.
6. Keep the phone powered on and connected to the internet whenever the website needs to send SMS. Wi-Fi is enough; mobile data can be turned off if Wi-Fi is available. The phone still needs normal cellular signal and an SMS-capable SIM for the actual SMS delivery.
7. Find the Android device ID in the SMS Gateway dashboard/device information. Use that ID as SMS_GATE_DEVICE_ID so the Vercel API targets the correct phone.
8. In Vercel, open Project -> Settings -> Environment Variables and add:
   SMS_GATE_URL=https://api.sms-gate.app/3rdparty/v1/messages
   SMS_GATE_USERNAME=<the Cloud Server username>
   SMS_GATE_PASSWORD=<the Cloud Server password>
   SMS_GATE_DEVICE_ID=<the Android device ID>
   SMS_GATE_SIM_NUMBER=1
9. Save the variables and redeploy the Vercel project so the serverless API receives the new environment variables.
10. Open the Ganapati Chasma Ghar website -> SMS Broadcast. First select only your own test number and send a short test message.
11. After the test succeeds, test with a small number of authorized recipients before using Select All.
12. Never place the gateway username/password in index.html, script.js, or other browser-side files.

OFFICIAL DOCUMENTATION
----------------------
Getting Started: https://docs.sms-gate.app/getting-started/
Installation: https://docs.sms-gate.app/installation/
Public Cloud Server: https://docs.sms-gate.app/getting-started/public-cloud-server/
Sending Messages API: https://docs.sms-gate.app/features/sending-messages/

NOTE ABOUT PHONE INTERNET
-------------------------
The public Cloud Server mode requires an active internet connection on the Android device. Wi-Fi satisfies this requirement; mobile data is not required if Wi-Fi is available. The SIM's cellular network is still used by Android to transmit the actual SMS.


LATEST CHANGES IN THIS BUILD
-----------------------------
- Settings is now a real sidebar section instead of opening the patient form.
- Settings includes a circular profile photo selector that accepts an image from the device gallery. The photo is resized and saved locally on the current device.
- Settings includes a name field below the profile photo and a Save Profile button.
- Settings includes a functional Dark Theme toggle. The preference is saved for the signed-in Firebase user on the current device.
- SMS Broadcast composer now allows up to 1000 WORDS instead of 160 characters. Very long messages may be split into multiple carrier SMS parts and can consume multiple SMS units.
- Reports remains in the code/data logic but is not shown as a left-sidebar tab.
- Medicines remains available in the patient form but is not shown as a left-sidebar tab.
- Previous Section / Back navigation is restored and now works by form section rather than only by individual field.

SMS GATEWAY QUICK SETUP
-----------------------
1. Put the clinic SIM in an Android phone.
2. Connect the Android phone to Wi-Fi. Mobile data may remain OFF.
3. Install SMS Gateway for Android and grant the required SMS permissions.
4. Enable Cloud Server in the app and connect the device.
5. Obtain the Cloud Server username, password, and Android device ID. Never share the password publicly.
6. In Vercel -> Project -> Settings -> Environment Variables, add:
   SMS_GATE_URL=https://api.sms-gate.app/3rdparty/v1/messages
   SMS_GATE_USERNAME=<Cloud Server username>
   SMS_GATE_PASSWORD=<Cloud Server password>
   SMS_GATE_DEVICE_ID=<Android device ID>
   SMS_GATE_SIM_NUMBER=1
7. Redeploy the Vercel project.
8. Keep the Android phone powered on, connected to Wi-Fi, connected to the SMS gateway, and with cellular signal whenever messages are being sent.
9. Test from SMS Broadcast using only your own phone number first.
10. After the test succeeds, test with a few authorized recipients before broadcasting to a larger group.

