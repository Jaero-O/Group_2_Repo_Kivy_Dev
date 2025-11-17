# Revised Mangofy App Entity-Relationship Diagram (ERD)

This document provides a revised, more scalable database schema for the Mangofy application.

## ERD Overview

This revised design normalizes the database schema to support disease and severity classification. It introduces `Disease` and `SeverityLevel` tables to separate static information from scan history, leading to a more organized and scalable system.

### Mermaid Diagram

```mermaid
erDiagram
    Disease {
        INTEGER id PK "Auto-incrementing primary key"
        TEXT name UQ "Unique name of the disease (e.g., 'Anthracnose')"
        TEXT description "Detailed description of the disease"
        TEXT symptoms "Common symptoms"
        TEXT prevention "Prevention and treatment methods"
    }
    SeverityLevel {
        INTEGER id PK "Auto-incrementing primary key"
        TEXT name UQ "e.g., Healthy, Early Stage, Advanced Stage"
        TEXT description "Description of the severity stage"
    }
    ScanRecord {
        INTEGER id PK "Auto-incrementing primary key"
        INTEGER disease_id FK "Foreign key to Disease table"
        INTEGER severity_level_id FK "Foreign key to SeverityLevel table"
        REAL severity_percentage "Calculated as (lesion_area / leaf_area)"
        TEXT image_path "File path to the saved scan image"
        DATETIME timestamp "The date and time of the scan"
    }

    ScanRecord ||--o{ Disease : "has"
    ScanRecord ||--o{ SeverityLevel : "is at"
```

### dbdiagram.io Code

```
Table ScanRecord {
  id integer [pk, increment]
  disease_id integer [ref: > Disease.id] // Foreign key
  image_path text [note: "File path to the saved scan image"]
  timestamp datetime [note: "The date and time of the scan"]
}

Table Disease {
  id integer [pk, increment]
  name text [unique, not null]
  description text
  symptoms text
  prevention text
}
```

## Explanation of Entities

### `Disease` Entity
This table acts as a central repository for information about each detectable condition.

*   **Attributes:**
    *   `id` (INTEGER, PK): A unique identifier for each disease.
    *   `name` (TEXT, Unique): The common name of the disease (e.g., "Anthracnose", "Healthy"). This will be used to look up the disease after the ML model gives a prediction.
    *   `description` (TEXT): A detailed explanation of the disease.
    *   `symptoms` (TEXT): A list or description of symptoms.
    *   `prevention` (TEXT): Information on how to prevent or treat the disease.

### `SeverityLevel` Entity
This table defines the classification stages for a disease.

*   **Attributes:**
    *   `id` (INTEGER, PK): A unique identifier for each severity level.
    *   `name` (TEXT, Unique): The name of the stage (e.g., "Healthy", "Early Stage", "Advanced Stage").
    *   `description` (TEXT): An explanation of what this stage entails.

### `ScanRecord` Entity
This table stores the history of every scan performed by the user.

*   **Attributes:**
    *   `id` (INTEGER, PK): A unique identifier for each scan record.
    *   `disease_id` (INTEGER, FK): A reference to the `id` in the `Disease` table. This efficiently links a scan to its result.
    *   `severity_level_id` (INTEGER, FK): A reference to the `id` in the `SeverityLevel` table.
    *   `severity_percentage` (REAL): The calculated ratio of the lesion area to the total leaf area, providing a quantitative measure of infection.
    *   `image_path` (TEXT): The local file path to the scanned image.
    *   `timestamp` (DATETIME): The date and time of the scan.