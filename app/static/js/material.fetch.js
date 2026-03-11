async function getMaterials(text) {
  try {
    const fetchUrl =  "http://192.168.99.14:5000/materials/query?text=" + encodeURIComponent(text);
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
