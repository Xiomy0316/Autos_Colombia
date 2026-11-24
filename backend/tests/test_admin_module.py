"""Pruebas del módulo de administración: equipo, turnos, vigencias y reportes."""


def test_new_parking_lot_starts_without_team_or_shifts(client):
    """La demo no siembra turnos; el único empleado es la cuenta de prueba."""
    employees = client.get("/api/employees").json()
    assert [item["full_name"] for item in employees] == ["Administrador de prueba"]
    assert client.get("/api/shifts").json() == []


def test_shift_and_employee_are_linked_to_the_parking_lot(client):
    shift = client.post("/api/shifts", json={
        "parking_lot_id": 1, "name": "Tarde", "starts_at": "14:00", "ends_at": "22:00", "notes": "Franja de prueba",
    })
    assert shift.status_code == 201, shift.text
    shift_id = shift.json()["id"]
    assert shift.json()["starts_at"] == "14:00"

    employee = client.post("/api/employees", json={
        "parking_lot_id": 1, "full_name": "Persona de prueba", "username": "persona.prueba", "role": "operator",
        "shift_id": shift_id,
    })
    assert employee.status_code == 201, employee.text
    assert employee.json()["role"] == "EMPLEADO"
    assert employee.json()["shift_id"] == shift_id

    shifts = client.get("/api/shifts").json()
    assert len(shifts) == 1
    assert [item["full_name"] for item in shifts[0]["employees"]] == ["Persona de prueba"]

    duplicate = client.post("/api/employees", json={
        "parking_lot_id": 1, "full_name": "Otra persona", "username": "persona.prueba",
    })
    assert duplicate.status_code == 409

    invalid_shift = client.post("/api/employees", json={
        "parking_lot_id": 1, "full_name": "Tercera persona", "username": "tercera", "shift_id": 9999,
    })
    assert invalid_shift.status_code == 422


def test_employee_can_be_moved_between_shifts_and_deactivated(client):
    morning = client.post("/api/shifts", json={
        "parking_lot_id": 1, "name": "Mañana", "starts_at": "06:00", "ends_at": "14:00",
    }).json()
    evening = client.post("/api/shifts", json={
        "parking_lot_id": 1, "name": "Noche", "starts_at": "18:00", "ends_at": "23:59",
    }).json()
    employee = client.post("/api/employees", json={
        "parking_lot_id": 1, "full_name": "Persona de prueba", "username": "persona.prueba", "shift_id": morning["id"],
    }).json()

    moved = client.patch(f"/api/employees/{employee['id']}", json={"shift_id": evening["id"]})
    assert moved.status_code == 200, moved.text
    assert moved.json()["shift_id"] == evening["id"]

    deactivated = client.patch(f"/api/employees/{employee['id']}", json={"active": False})
    assert deactivated.status_code == 200
    assert deactivated.json()["active"] is False


def test_new_tariff_closes_the_previous_validity(client):
    """Al crear una vigencia se cierra la anterior el día previo, sin solapar periodos."""
    history = client.get("/api/tariffs/history").json()
    assert history, "la demostración incluye tarifas iniciales"
    current = next(item for item in history if item["vehicle_type_id"] == 1)
    assert current["effective_until"] is None

    new_tariff = client.post("/api/tariffs", json={
        "vehicle_type_id": 1, "amount": 270000, "effective_from": "2027-01-01", "note": "Vigencia 2027",
    })
    assert new_tariff.status_code == 201, new_tariff.text
    assert new_tariff.json()["effective_until"] is None

    closed = next(item for item in client.get("/api/tariffs/history").json() if item["id"] == current["id"])
    assert closed["effective_until"] == "2026-12-31"

    overlapping = client.post("/api/tariffs", json={
        "vehicle_type_id": 1, "amount": 280000, "effective_from": "2027-01-01", "effective_until": "2027-06-30",
    })
    assert overlapping.status_code == 409

    invalid = client.post("/api/tariffs", json={
        "vehicle_type_id": 1, "amount": 280000, "effective_from": "2027-06-30", "effective_until": "2027-01-01",
    })
    assert invalid.status_code == 422


def test_reports_and_activity_describe_the_current_state(client):
    report = client.get("/api/reports").json()
    assert report["indicators"]["cells_total"] == 12
    assert report["indicators"]["cells_available"] == 12
    assert report["inventory"]
    assert report["flow"] == {"entries": 0, "exits": 0, "inside_at_start": 0, "inside_now": 0}
    assert report["monthly"] == {"active": 0, "expiring_soon": 0, "expired": 0}

    assert client.get("/api/activity").json() == []

    customer = client.post("/api/customers", json={
        "parking_lot_id": 1, "document_type": "CC", "document_number": "900111222",
        "full_name": "Cliente de prueba", "phone": "", "email": "",
    })
    assert customer.status_code == 201
    vehicle = client.post("/api/vehicles", json={
        "parking_lot_id": 1, "customer_id": customer.json()["id"], "vehicle_type_id": 1,
        "plate": "TEST01", "brand": "Prueba", "color": "Verde",
    })
    assert vehicle.status_code == 201, vehicle.text
    payment = client.post("/api/payments", json={"vehicle_id": vehicle.json()["id"], "months": 1, "method": "CASH"})
    assert payment.status_code == 201, payment.text

    activity = client.get("/api/activity").json()
    assert activity, "el pago queda registrado en la actividad"
    assert activity[0]["kind"] == "PAYMENT"
    assert "TEST01" in activity[0]["operation"]
    assert activity[0]["employee"] == "Administrador de prueba"

    updated = client.get("/api/reports").json()
    assert updated["indicators"]["customers"] == 1
    assert updated["monthly"]["active"] == 1
    assert updated["payments_by_method"]


def test_update_site_and_prevent_duplicate_names(client):
    """Verifica la actualización de sedes y sus validaciones."""

    site_a = client.post("/api/sites", json={
        "parking_lot_id": 1,
        "name": "Sede Prueba EA2 Norte",
        "address": "Calle 10",
    })
    assert site_a.status_code == 201, site_a.text

    site_b = client.post("/api/sites", json={
        "parking_lot_id": 1,
        "name": "Sede Prueba EA2 Sur",
        "address": "Calle 20",
    })
    assert site_b.status_code == 201, site_b.text

    site_id = site_a.json()["id"]

    updated = client.patch(f"/api/sites/{site_id}", json={
        "name": "  Sede Prueba EA2 Centro  ",
        "address": "  Calle 30  ",
    })

    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Sede Prueba EA2 Centro"
    assert updated.json()["address"] == "Calle 30"

    sites = client.get("/api/sites")
    assert sites.status_code == 200
    assert any(
        site["id"] == site_id
        and site["name"] == "Sede Prueba EA2 Centro"
        for site in sites.json()
    )

    duplicate = client.patch(f"/api/sites/{site_id}", json={
        "name": "  sede prueba ea2 sur  ",
    })
    assert duplicate.status_code == 409

    empty_name = client.patch(f"/api/sites/{site_id}", json={
        "name": "   ",
    })
    assert empty_name.status_code == 422

    missing = client.patch("/api/sites/99999", json={
        "name": "Sede inexistente",
    })
    assert missing.status_code == 404


def test_update_zone_and_prevent_duplicate_names(client):
    """Verifica la actualización de zonas y sus validaciones."""

    site = client.post("/api/sites", json={
        "parking_lot_id": 1,
        "name": "Sede Prueba Zonas EA2",
        "address": "Calle 40",
    })
    assert site.status_code == 201, site.text

    site_id = site.json()["id"]

    zone_a = client.post("/api/zones", json={
        "site_id": site_id,
        "name": "Zona Prueba EA2 A",
        "code": "A",
    })
    assert zone_a.status_code == 201, zone_a.text

    zone_b = client.post("/api/zones", json={
        "site_id": site_id,
        "name": "Zona Prueba EA2 B",
        "code": "B",
    })
    assert zone_b.status_code == 201, zone_b.text

    zone_id = zone_a.json()["id"]

    updated = client.patch(f"/api/zones/{zone_id}", json={
        "name": "  Zona EA2 Actualizada  ",
        "code": "  n-01  ",
    })

    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Zona EA2 Actualizada"
    assert updated.json()["code"] == "N-01"
    assert updated.json()["site_id"] == site_id

    zones = client.get("/api/zones", params={
        "site_id": site_id,
    })
    assert zones.status_code == 200
    assert any(
        zone["id"] == zone_id
        and zone["name"] == "Zona EA2 Actualizada"
        for zone in zones.json()
    )

    duplicate = client.patch(f"/api/zones/{zone_id}", json={
        "name": "  zona prueba ea2 b  ",
    })
    assert duplicate.status_code == 409

    empty_name = client.patch(f"/api/zones/{zone_id}", json={
        "name": "   ",
    })
    assert empty_name.status_code == 422

    missing = client.patch("/api/zones/99999", json={
        "name": "Zona inexistente",
    })
    assert missing.status_code == 404


def test_employee_cannot_update_sites_or_zones(employee_client):
    """El empleado no puede modificar sedes ni zonas."""

    site_response = employee_client.patch(
        "/api/sites/99999",
        json={"name": "Cambio no autorizado"},
    )
    assert site_response.status_code == 403

    zone_response = employee_client.patch(
        "/api/zones/99999",
        json={"name": "Cambio no autorizado"},
    )
    assert zone_response.status_code == 403



def test_admin_can_delete_cell_without_history(client):
    """El administrador puede eliminar una celda nueva sin historial."""

    response = client.get("/api/cells")
    assert response.status_code == 200, response.text

    existing_cells = response.json()

    reference_cell = next(
        (cell for cell in existing_cells if cell["compatible_types"]),
        None,
    )

    assert reference_cell is not None, (
        "Se necesita una celda con tipos compatibles para la prueba"
    )

    new_cell = client.post("/api/cells", json={
        "zone_id": reference_cell["zone_id"],
        "code": "EA2DEL999",
        "description": "Celda creada para prueba de eliminación",
        "compatible_type_ids": [
            vehicle_type["id"]
            for vehicle_type in reference_cell["compatible_types"]
        ],
    })

    assert new_cell.status_code == 201, new_cell.text

    cell_id = new_cell.json()["id"]

    deleted = client.delete(f"/api/cells/{cell_id}")

    assert deleted.status_code == 200, deleted.text
    assert "eliminada" in deleted.json()["detail"].lower()

    remaining_cells = client.get("/api/cells")
    assert remaining_cells.status_code == 200

    assert all(
        cell["id"] != cell_id
        for cell in remaining_cells.json()
    )

    deleted_again = client.delete(f"/api/cells/{cell_id}")
    assert deleted_again.status_code == 404


def test_employee_cannot_delete_cells(employee_client):
    """El empleado no tiene permiso para eliminar celdas."""

    response = employee_client.delete("/api/cells/1")

    assert response.status_code == 403
