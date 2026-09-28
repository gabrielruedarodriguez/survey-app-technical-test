<script setup>
import { onMounted, ref } from "vue";
import { getSurveyResults } from "./api";

const surveyId = 1;
const data = ref(null);
const loading = ref(false);
const error = ref("");

async function loadResults() {
  loading.value = true;
  error.value = "";
  try {
    data.value = await getSurveyResults(surveyId);
  } catch (exception) {
    error.value = exception.message;
  } finally {
    loading.value = false;
  }
}

onMounted(loadResults);
</script>

<template>
  <main>
    <h1>{{ data?.survey?.title || "Survey results" }}</h1>

    <p v-if="loading">Loading...</p>
    <p v-else-if="error" class="error">{{ error }}</p>

    <template v-else-if="data">
      <p>{{ data.count }} responses</p>
      <table>
        <thead>
          <tr>
            <th>External ID</th>
            <th>Status</th>
            <th>Submitted</th>
            <th>Answers</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in data.results" :key="item.id">
            <td>{{ item.external_id }}</td>
            <td>{{ item.status }}</td>
            <td>{{ new Date(item.submitted_at).toLocaleString() }}</td>
            <td><code>{{ JSON.stringify(item.answers) }}</code></td>
          </tr>
        </tbody>
      </table>
    </template>
  </main>
</template>

<style>
body {
  margin: 0;
  background: #f5f7fb;
  color: #1f2937;
  font-family: Inter, system-ui, sans-serif;
}

main {
  max-width: 960px;
  margin: 48px auto;
  padding: 32px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgb(15 23 42 / 8%);
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  padding: 12px;
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
}

.error {
  color: #b91c1c;
}
</style>
