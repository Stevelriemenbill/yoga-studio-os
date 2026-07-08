import pytest

from tests.test_booking import (
    _auth_headers,
    _make_course,
    _make_member,
    _make_session,
)


async def _make_program(client, headers, **overrides):
    payload = {
        "name": "2-Jahres-Yogalehrerausbildung",
        "description": "Ausbildung",
        "duration_months": 24,
        **overrides,
    }
    resp = await client.post("/api/v1/training/programs", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _make_cohort(client, headers, program_id, **overrides):
    payload = {
        "program_id": program_id,
        "name": "Frühjahr 2026",
        "start_date": "2026-03-01",
        "end_date": "2028-03-01",
        **overrides,
    }
    resp = await client.post("/api/v1/training/cohorts", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_program_and_cohort_crud(client):
    headers = await _auth_headers(client)
    program = await _make_program(client, headers)
    assert program["duration_months"] == 24

    programs = (await client.get("/api/v1/training/programs", headers=headers)).json()
    assert len(programs) == 1

    cohort = await _make_cohort(client, headers, program["id"])
    assert cohort["status"] == "planned"
    assert cohort["enrolled_count"] == 0

    # Filter cohorts by program.
    listed = (
        await client.get(
            f"/api/v1/training/cohorts?program_id={program['id']}", headers=headers
        )
    ).json()
    assert len(listed) == 1

    # Move cohort to running.
    patched = await client.patch(
        f"/api/v1/training/cohorts/{cohort['id']}",
        json={"status": "running"},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["status"] == "running"


@pytest.mark.asyncio
async def test_enroll_and_prevent_duplicate(client):
    headers = await _auth_headers(client)
    program = await _make_program(client, headers)
    cohort = await _make_cohort(client, headers, program["id"])
    member = await _make_member(client, headers)

    resp = await client.post(
        f"/api/v1/training/cohorts/{cohort['id']}/enrollments",
        json={"member_id": member["id"]},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "active"

    # Cohort now reports one enrolled trainee.
    listed = (await client.get("/api/v1/training/cohorts", headers=headers)).json()
    assert listed[0]["enrolled_count"] == 1

    # Second enrollment of the same member is rejected.
    dup = await client.post(
        f"/api/v1/training/cohorts/{cohort['id']}/enrollments",
        json={"member_id": member["id"]},
        headers=headers,
    )
    assert dup.status_code == 409, dup.text

    # Enrollment listing includes the member name.
    enrollments = (
        await client.get(
            f"/api/v1/training/cohorts/{cohort['id']}/enrollments", headers=headers
        )
    ).json()
    assert enrollments[0]["member_name"] == "Anna Muster"


@pytest.mark.asyncio
async def test_cohort_progress_counts_attended_hours(client):
    headers = await _auth_headers(client)
    program = await _make_program(client, headers)

    # Required hours for the program (soll).
    req = await client.post(
        "/api/v1/training/requirements",
        json={
            "name": "Praxis",
            "area": "practice",
            "required_hours": 500,
            "program_id": program["id"],
        },
        headers=headers,
    )
    assert req.status_code == 201, req.text

    cohort = await _make_cohort(client, headers, program["id"])
    member = await _make_member(client, headers)
    await client.post(
        f"/api/v1/training/cohorts/{cohort['id']}/enrollments",
        json={"member_id": member["id"]},
        headers=headers,
    )

    course = await _make_course(client, headers, duration_minutes=120)

    # A weekend session NOT attached to the cohort, but attended: must NOT count.
    other = await _make_session(
        client, headers, course["id"], starts_at="2026-04-01T09:00:00"
    )
    await client.put(
        f"/api/v1/attendance/session/{other['id']}",
        json={"member_id": member["id"], "status": "present"},
        headers=headers,
    )

    # A cohort weekend session (2h), attended: counts.
    cohort_session = await client.post(
        f"/api/v1/courses/{course['id']}/sessions",
        json={
            "course_id": course["id"],
            "starts_at": "2026-05-13T09:00:00",
            "cohort_id": cohort["id"],
        },
        headers=headers,
    )
    assert cohort_session.status_code == 201, cohort_session.text
    cs = cohort_session.json()
    assert cs["cohort_id"] == cohort["id"]

    await client.put(
        f"/api/v1/attendance/session/{cs['id']}",
        json={"member_id": member["id"], "status": "present"},
        headers=headers,
    )

    progress = (
        await client.get(
            f"/api/v1/training/cohorts/{cohort['id']}/progress", headers=headers
        )
    ).json()
    assert progress["required_hours"] == 500.0
    assert len(progress["trainees"]) == 1
    trainee = progress["trainees"][0]
    assert trainee["member_name"] == "Anna Muster"
    # Only the cohort-attached session (2h) counts; the unattached one does not.
    assert trainee["attended_sessions"] == 1
    assert trainee["training_hours"] == 2.0


@pytest.mark.asyncio
async def test_recurring_every_six_weeks(client):
    headers = await _auth_headers(client)
    program = await _make_program(client, headers)
    cohort = await _make_cohort(client, headers, program["id"])
    course = await _make_course(client, headers)

    resp = await client.post(
        f"/api/v1/courses/{course['id']}/schedule",
        json={
            "course_id": course["id"],
            "weekdays": [5],  # Saturdays
            "start_time": "09:00:00",
            "start_date": "2026-03-07",
            "count": 4,
            "interval_weeks": 6,
            "cohort_id": cohort["id"],
        },
        headers=headers,
    )
    assert resp.status_code in (200, 201), resp.text
    sessions = resp.json()
    assert len(sessions) == 4
    # All share one series and belong to the cohort.
    assert len({s["series_id"] for s in sessions}) == 1
    assert all(s["cohort_id"] == cohort["id"] for s in sessions)
    # Six weeks (42 days) apart.
    dates = sorted(s["starts_at"][:10] for s in sessions)
    assert dates[0] == "2026-03-07"
    assert dates[1] == "2026-04-18"
