const credentials = btoa("ana:ana123");

export async function getSurveyResults(surveyId, filters = {}) {
  const params = new URLSearchParams(
    Object.entries(filters).filter(([, value]) => value)
  );
  const query = params.toString();
  const url = `/api/surveys/${surveyId}/results/${query ? `?${query}` : ""}`;
  const response = await fetch(url, {
    headers: { Authorization: `Basic ${credentials}` },
  });

  if (!response.ok) {
    throw new Error(await readError(response));
  }

  return response.json();
}

async function readError(response) {
  const body = await response.json().catch(() => null);
  if (!body) {
    return `Request failed with status ${response.status}`;
  }
  if (body.detail) {
    return body.detail;
  }
  return Object.entries(body)
    .map(([field, messages]) => `${field}: ${[].concat(messages).join(" ")}`)
    .join(" ");
}
