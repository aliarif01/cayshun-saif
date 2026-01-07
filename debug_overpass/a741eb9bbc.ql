[out:json][timeout:25];
(
  node["amenity"="cafe"](around:500,53.4794,-2.2453);
  way["amenity"="cafe"](around:500,53.4794,-2.2453);
  relation["amenity"="cafe"](around:500,53.4794,-2.2453);
  node["shop"="coffee"](around:500,53.4794,-2.2453);
  way["shop"="coffee"](around:500,53.4794,-2.2453);
  relation["shop"="coffee"](around:500,53.4794,-2.2453);
);
out tags center;
>;
out skel qt;