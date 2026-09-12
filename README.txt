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
- Previous Section button now steps back one field at a time through every input/select/textarea on the form (in on-screen order), instead of only jumping between 7 fixed landmark fields.


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
