const credentials = btoa("ana:ana123");

export async function getSurveyResults(surveyId) {
  const response = await fetch(`/api/surveys/${surveyId}/results/`, {
    headers: { Authorization: `Basic ${credentials}` },
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return response.json();
}

