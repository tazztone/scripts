with open("userscripts/toppreise/tests/mock_toppreise.html", "r") as f:
    content = f.read()

# Add a test card that reproduces the user's specific case:
# Visible price: CHF 37.95
# Competing reference price: CHF 47.82
# Historical low: CHF 37.95

# Find where to insert the new card
insert_point = "<!-- Card 2: Expensive Store Product -->"

new_card = """                <!-- Card 1.5: Regression Fixture for Competing Reference Price -->
                <a href="/preisvergleich/PC-Zubehoer/Endgame-Gear-XM2w-p1003795" id="card-competing-reference" class="Plugin_Product medium-box mixedBrowsingList col-12 col-sm-6 col-lg-4 col-xxxl-3" data-entity-id="1003795">
                  <div class="row h-100">
                    <div class="col-auto p-0">
                      <div class="image_container">
                        <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='60' height='60'%3E%3Crect width='60' height='60' fill='%23334155'/%3E%3C/svg%3E" alt="Endgame Gear XM2w 4k Wireless" />
                      </div>
                    </div>
                    <div class="col d-flex flex-column justify-content-between">
                      <div class="product-name">ENDGAME GEAR XM2w 4k Wireless Gaming Mouse</div>

                      <!-- Some rogue reference price hanging out in a hidden element or nearby -->
                      <div class="Plugin_Price" style="display: none;">47.82</div>

                      <div class="Plugin_PriceInformation price_information_product">
                        <div class="priceContainer productPrice">ab <span class="currency">CHF </span><div class="Plugin_Price">37.95</div></div>
                      </div>

                      <!-- Store row might have the 47.82 price -->
                      <div class="Plugin_DealerRelProdPriceInfo">
                        <span class="title">CompetingStore</span>
                        <div class="productPrice"><div class="Plugin_Price">CHF 47.82</div></div>
                      </div>
                      <div class="offersCount">2 Angebote</div>
                    </div>
                  </div>
                  <div class="badge badge-dif m_26_50"><div class="text">Aufschlag</div><p>+26%</p></div>
                </a>

"""

content = content.replace(insert_point, new_card + insert_point)

# Add the fake pricechart endpoint for this product
chart_endpoint = """        if (urlParams.get('p_pc_pid') === '797571') {"""
new_endpoint = """        if (urlParams.get('p_pc_pid') === '1003795') {
            document.getElementById('ajax-response').innerHTML = `
                <div class="PriceChartLegend">
                  <div class="col-4"><div class="title">aktueller Toppreis</div><div class="Plugin_Price">37.95</div></div>
                  <div class="col-4"><div class="title">Tiefstpreis</div><div class="Plugin_Price">37.95</div></div>
                  <div class="col-4"><div class="title">Höchstpreis</div><div class="Plugin_Price">55.00</div></div>
                </div>`;
            return;
        }
"""
content = content.replace(chart_endpoint, new_endpoint + chart_endpoint)


with open("userscripts/toppreise/tests/mock_toppreise.html", "w") as f:
    f.write(content)
