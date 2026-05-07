# shopping_list.feature
# CMSC 471 Final Project — BDD Specification
# Each scenario maps to a User Story on the Azure DevOps board (AB#)

Feature: AI-Powered Shopping List Processing
  As a user
  I want to upload a photo of my handwritten shopping list
  So that my items are automatically extracted and stored digitally

  # ── User Story 1: Upload a shopping list photo ──────────────────────────────
  # AB#1 - As a user, I want to upload a handwritten shopping list photo
  #        so that the system can extract my items automatically.

  Scenario: Successful image upload
    Given I am on the Shopping List AI home page
    And I have a photo of a handwritten shopping list
    When I select the photo file using the upload button
    And I click "Upload & Process"
    Then the image should be sent to the API
    And I should receive a job ID in the response
    And the status should show "Uploading image..."

  Scenario: Upload rejected when no file is selected
    Given I am on the Shopping List AI home page
    And no file has been selected
    When I click "Upload & Process"
    Then I should see an error message "Please select an image file first."
    And no API call should be made

  # ── User Story 2: Poll for processing status ────────────────────────────────
  # AB#2 - As a user, I want to see the processing status of my upload
  #        so that I know when my items are ready to view.

  Scenario: Polling shows IN_PROGRESS status
    Given I have submitted a shopping list image
    And the job status in DynamoDB is "IN_PROGRESS"
    When the front end polls the /poll/{job_id} endpoint
    Then the status box should display "Processing..."
    And the upload button should remain disabled

  Scenario: Polling detects COMPLETE status
    Given I have submitted a shopping list image
    And the Step Functions state machine has finished successfully
    And the job status in DynamoDB is "COMPLETE"
    When the front end polls the /poll/{job_id} endpoint
    Then the status box should display "Done! X item(s) extracted."
    And the records table should automatically refresh

  Scenario: Polling detects FAILED status
    Given I have submitted a shopping list image
    And the Step Functions state machine has encountered an error
    And the job status in DynamoDB is "FAILED"
    When the front end polls the /poll/{job_id} endpoint
    Then the status box should display "Processing failed. Please try again."
    And the upload button should be re-enabled

  # ── User Story 3: View extracted shopping list items ────────────────────────
  # AB#3 - As a user, I want to view all my extracted shopping list items
  #        so that I can see what was recognized from my photo.

  Scenario: Records table displays all items
    Given the Records DynamoDB table contains shopping list items
    When I load the Shopping List AI home page
    Then the records table should display all items
    And each row should show the item name, source image, and date added

  Scenario: Records table shows empty state
    Given the Records DynamoDB table contains no items
    When I load the Shopping List AI home page
    Then I should see the message "No items yet. Upload a photo to get started."

  # ── User Story 4: Delete a shopping list item ───────────────────────────────
  # AB#4 - As a user, I want to delete individual shopping list items
  #        so that I can remove items I no longer need.

  Scenario: Successfully delete a single item
    Given the records table displays at least one shopping list item
    When I click the "Delete" button next to an item
    And I confirm the deletion in the confirmation dialog
    Then a DELETE request should be sent to /records/{record_id}
    And the item row should be removed from the table
    And the remaining items should still be displayed

  Scenario: Deleting last item for a job cleans up S3 and job record
    Given a job has exactly one remaining record in the Records table
    When I delete that record
    Then the Records Lambda should also delete the source image from S3
    And the job entry should be removed from the Jobs DynamoDB table

  Scenario: User cancels deletion
    Given the records table displays at least one shopping list item
    When I click the "Delete" button next to an item
    And I click "Cancel" in the confirmation dialog
    Then no DELETE request should be sent
    And the item should remain in the table

  # ── User Story 5: Health check confirms API is live ─────────────────────────
  # AB#5 - As a developer, I want a health check endpoint
  #        so that I can confirm the API is deployed and reachable.

  Scenario: Health check returns 200 OK
    Given the Shopping List API is deployed to AWS
    When a GET request is sent to /health
    Then the response status code should be 200
    And the response body should contain "status": "ok"
    And the response body should contain "Shopping List API is healthy."

  Scenario: Health check is reachable from the browser
    Given the Shopping List API is deployed to AWS
    When I navigate to the /health endpoint in a browser
    Then I should see a JSON response with status "ok"
