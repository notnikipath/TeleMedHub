from locust import HttpUser, between, task


class TeleMedUser(HttpUser):
    wait_time = between(0.2, 1.0)

    @task(3)
    def health(self):
        self.client.get("/health")

    @task(2)
    def services_health(self):
        self.client.get("/services/health")

    @task(1)
    def recommend_doctor(self):
        payload = {
            "patient_id": "PAT-LOAD",
            "complaint_text": "Головная боль и высокое давление",
            "actor_role": "patient",
        }
        self.client.post("/recommend/doctor", json=payload)
