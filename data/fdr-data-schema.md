# FDR Data Schema Specification

## Overview

The Foundational Data Refresh (FDR) schema defines two entity types — **Facilities** and **NGOs** — that share a common base of organization fields. Data is extracted from web scrapes via LLM, meaning every field represents a *claim derived from text*, not verified ground truth.

**Dataset**: 987 facility records (Ghana scope)
**Source**: Web scraping + LLM extraction
**Format**: CSV with JSON array fields

---

## Entity Extraction (Source Text Metadata)

These fields capture what named entities were identified in the source text during extraction.

| Field | Type | Definition |
|---|---|---|
| `ngos` | list[str] | NGO names present in the text. An NGO is any non-profit organization that delivers tangible, on-the-ground healthcare services in low- or lower-middle-income settings. |
| `facilities` | list[str] | Healthcare facility names present in the text. A publishable healthcare facility is any physical site that is currently operating and delivers in-person medical diagnosis or treatment to patients. |
| `other_organizations` | list[str] | Named entities that don't meet facility or NGO classifications. |

---

## Base Organization Fields (Shared by Facilities and NGOs)

### Contact Information

| Field | Type | Definition |
|---|---|---|
| `name` | str | Official name of the organization. Complete, unabbreviated form with proper capitalization, excluding business suffixes like "Ltd", "LLC", "Inc". |
| `phone_numbers` | list[str] | The organization's phone numbers in E164 format (e.g., `+233392022664`). |
| `officialPhone` | str | Official phone number associated with the organization in E164 format. Must be the organization's primary official contact number. |
| `email` | str | The organization's primary email address. |

### Web Presence

| Field | Type | Definition |
|---|---|---|
| `websites` | list[str] | Websites associated with the organization. |
| `officialWebsite` | str | Official website associated with the organization. Domain name only (not full URL). Must correspond to the organization's official website. |
| `facebookLink` | str | URL to the organization's Facebook page. |
| `twitterLink` | str | URL to the organization's Twitter profile. |
| `linkedinLink` | str | URL to the organization's LinkedIn page. |
| `instagramLink` | str | Instagram account URL. |
| `logo` | str | URL linking to the organization's logo image. |

### General

| Field | Type | Definition |
|---|---|---|
| `yearEstablished` | int | The year in which the organization was established. |
| `acceptsVolunteers` | bool | Indicates whether the organization accepts clinical volunteers. |

### Address

| Field | Type | Definition |
|---|---|---|
| `address_line1` | str | Street address only (building number, street name). Does NOT include city, state, or country. |
| `address_line2` | str | Additional street address information (apartment, suite, building name). |
| `address_line3` | str | Third line of street address if needed. |
| `address_city` | str | City or town name. Parsed from comma-separated location strings if needed. |
| `address_stateOrRegion` | str | State, region, or province. Parsed from comma-separated location strings if needed. |
| `address_zipOrPostcode` | str | ZIP or postal code. |
| `address_country` | str | Full country name. Extracted using contextual clues from URL domain, phone numbers, or website content if not explicitly stated. |
| `address_countryCode` | str | ISO alpha-2 country code. Derived from country name if needed — **required** when country is known. |

---

## Facility-Specific Fields

### Structured Attributes

| Field | Type | Values / Definition |
|---|---|---|
| `facilityTypeId` | enum | Type of facility. Values: `hospital`, `pharmacy`, `doctor`, `clinic`, `dentist` |
| `operatorTypeId` | enum | Public or private operation. Values: `public`, `private` |
| `affiliationTypeIds` | list[enum] | Facility affiliations (one or more). Values: `faith-tradition`, `philanthropy-legacy`, `community`, `academic`, `government` |
| `description` | str | A brief paragraph describing the facility's services and/or history. |
| `area` | int | Total floor area of the facility in square meters. |
| `numberDoctors` | int | Total number of medical doctors working at the facility. |
| `capacity` | int | Overall inpatient bed capacity of the facility. |

### Medical Specialties

| Field | Type | Definition |
|---|---|---|
| `specialties` | list[str] | Medical specialties associated with the organization. Uses exact case-sensitive matches from a controlled specialty hierarchy. Choose the most specific appropriate specialty; only predict specialties clearly mentioned or strongly implied. |

**Controlled Specialty Values** (partial list from schema):

`internalMedicine`, `familyMedicine`, `pediatrics`, `cardiology`, `generalSurgery`, `emergencyMedicine`, `gynecologyAndObstetrics`, `orthopedicSurgery`, `dentistry`, `ophthalmology`

### Free-Text Facility Facts

These three fields contain **lists of declarative statements** extracted by LLM from source text. Each entry is a standalone, citable fact about the facility.

#### `procedure` — list[str]

Specific clinical services performed at the facility — medical/surgical interventions and diagnostic procedures and screenings (e.g., operations, endoscopy, imaging- or lab-based tests).

Each fact should be a clear, declarative statement including specific quantities when available.

**Examples**:
- "Offers hemodialysis treatment 3 times weekly"
- "Performs cataract surgery using phacoemulsification technique"
- "Conducts routine prenatal ultrasound screening"

#### `equipment` — list[str]

Physical medical devices and infrastructure — imaging machines (MRI/CT/X-ray), surgical/OR technologies, monitors, laboratory analyzers, and critical utilities (e.g., piped oxygen/oxygen plants, backup power).

Include specific models when available.

**Examples**:
- "Has Siemens SOMATOM Force dual-source CT scanner"
- "Equipped with backup diesel generator"
- "Has 2 operating theatres with laminar airflow"

#### `capability` — list[str]

Medical capabilities defining what level and types of clinical care the facility can deliver — trauma/emergency care levels, specialized units (ICU/NICU/burn unit), clinical programs (stroke care, IVF), diagnostic capabilities, clinical accreditations, care setting (inpatient/outpatient), staffing levels, and patient capacity.

**Excludes**: addresses, contact info, business hours, and pricing.

**Examples**:
- "Level II trauma center"
- "Joint Commission accredited"
- "Operates a 12-bed NICU"
- "Provides 24/7 emergency services"

---

## NGO-Specific Fields

| Field | Type | Definition |
|---|---|---|
| `countries` | list[str] | Countries where the NGO operates (array of ISO alpha-2 codes). |
| `missionStatement` | str | The NGO's formal mission statement. |
| `missionStatementLink` | str | A URL to the NGO's published mission statement. |
| `organizationDescription` | str | A neutral, factual description derived from the mission statement. Removes explicitly religious or subjective language. |

---

## Schema Analysis: Implications for VirtueCommand

### Data Quality Tiers

| Tier | Fields | Query Method | Reliability |
|---|---|---|---|
| **Structured** | `name`, `facilityTypeId`, `operatorTypeId`, `affiliationTypeIds`, `capacity`, `numberDoctors`, `area`, `specialties`, `address_*`, `yearEstablished` | SQL (direct filter, count, aggregate) | High when populated; expect sparse numeric fields |
| **Semi-Structured Lists** | `specialties`, `ngos`, `facilities`, `countries`, `affiliationTypeIds` | SQL with array operations | Medium — controlled vocabulary for specialties; entity extraction for others |
| **Free-Text Facts** | `procedure`, `equipment`, `capability`, `description`, `organizationDescription`, `missionStatement` | Vector search (embeddings) + Self-RAG | Variable — each statement is an LLM-extracted claim from web scrape |

### Known Gaps

| Gap | Impact | Mitigation |
|---|---|---|
| **No coordinates (lat/lng)** | Cannot do geospatial analysis without geocoding from `address_city` | Geocoding pipeline required; accuracy degrades for rural facilities |
| **No per-claim provenance** | Cannot trace individual procedure/equipment claims to specific source URLs | Track source at record level; flag single-source records |
| **No temporal metadata per claim** | Cannot distinguish current vs. outdated capabilities within a record | Parse temporal language from free text ("since 2019", "3 times weekly") |
| **Coarse facility taxonomy** | 5 types (hospital/clinic/pharmacy/doctor/dentist) don't map to Ghana's tiered system (CHPS → Health Center → District → Regional → Teaching Hospital) | Infer tier from `capacity`, `numberDoctors`, `capability` text |
| **`procedure` / `capability` overlap** | Same clinical fact could appear in either field | Vector search must query both fields for clinical questions |
| **Sparse numeric fields** | `numberDoctors`, `capacity`, `area` likely have high missingness | Anomaly detection (procedure-to-doctor ratios) only works where data exists; flag when data is absent |
