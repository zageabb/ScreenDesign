# Screen Designer – How to Use

This guide explains how to run the app, explore lists and forms, and make the most of repeatable tables and calculated fields.

## 1. Start the application

1. Create and activate a virtual environment.
2. Install dependencies from `requirements.txt`.
3. Initialize the database, load the JSON screen schemas, then start the development server:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   pip install -r requirements.txt

   export FLASK_APP=app.py  # Windows: set FLASK_APP=app.py
   flask --app app.py db-init
   flask --app app.py load-schemas
   flask --app app.py run --debug --port 5004
   ```
4. Open the desired screen, such as the sample vehicle form at `http://127.0.0.1:5004/screen/vehicle`.

## 2. Navigate to a screen

* Browse to `/screen/<slug>?list=1` to see the list page for a screen. Each row shows its ID, the configured columns, and **New**/**Edit**/**Delete** actions.
* Selecting **New** opens the creation form. Selecting a row ID or **Edit** opens the edit form for that record.

## 3. Understand list columns

* List tables always include the record ID and any column names defined in the screen JSON under the top-level `"columns"` array (for example, registration, mileage, and notes in the sample vehicle schema).
* If a schema does not declare `"columns"`, every top-level field name is displayed instead.

## 4. Fill out forms

* Forms render according to the screen JSON definition, including one-column, two-column, or table layouts.
* Repeatable tables (fields with `"type": "group"` and `"mode": "repeatable-table"`) display as an embedded grid.
  * Use **Add Row** to append a new row that is prefilled with each sub-field’s defaults.
  * Update values directly inside the grid; use the row **Delete** buttons to remove entries.

## 5. Work with calculated fields

* Fields (including those inside repeatable tables) can declare a `"compute"` expression. The server always recomputes these expressions so saved data stays authoritative.
* Use the **Refresh Calculations** button on the form to ask the server for a preview of every calculated field before saving.
* When you submit the form, calculations refresh automatically to ensure the saved record reflects the latest expressions.

## 6. Save or delete a record

* Click **Save** to persist your changes. After the request succeeds you will either see a confirmation or be redirected back to the list, depending on the screen configuration.
* Use the **Delete** button on a record to remove it. You will be asked to confirm before the record is deleted and you are returned to the list view.

## 7. Configure the experience

* Edit the JSON schema for a screen to:
  * Add or reorder list columns by updating the `"columns"` array.
  * Control layout and defaults for every form field.
  * Add child screens (via the `children` array) so buttons on the form link to related lists or forms.
  * Add or adjust `"compute"` expressions for calculated fields.

Reload schemas after making JSON changes so the server picks up your updates.
