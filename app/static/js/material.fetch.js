const API_BASE = window.location.origin;

async function getMaterials(text) {
  try {
    const fetchUrl =  API_BASE + "/materials/query?text=" + encodeURIComponent(text);
    const response = await fetch(fetchUrl);

    if (!response.ok) {
      throw new Error("Request failed");
    }

    const data = await response.json();
    //console.log("Received data:", data);
    return data;
  } catch (error) {
    console.error("Error:", error);
  }

}
