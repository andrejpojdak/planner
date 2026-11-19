
async function getPrices(material) {
  try {
    const fetchUrl =  API_BASE + "/orders/query_sales_price?material=" + encodeURIComponent(material);
    const response = await fetch(fetchUrl);

    if (!response.ok) {
      throw new Error("Request failed");
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error:", error);
  }

}
