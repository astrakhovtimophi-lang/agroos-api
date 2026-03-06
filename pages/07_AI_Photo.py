import numpy as np
import streamlit as st
from i18n import tr
from PIL import Image

from agro_utils import append_photo_diag, add_event, field_names_and_features, now_iso
from styles import apply_styles

apply_styles()

st.title(tr("module_photo_diag"))
st.caption("Upload a photo, mark visible symptoms, and get probability-based diagnosis + action plan.")


def softmax(x):
    z = np.array(x, dtype="float64")
    z = z - np.max(z)
    e = np.exp(z)
    return e / np.sum(e)


def analyze_image(img: Image.Image):
    arr = np.array(img.convert("RGB"), dtype="float32")
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]

    brightness = 0.299 * r + 0.587 * g + 0.114 * b
    green_ratio = float(((g > r * 1.05) & (g > b * 1.05)).mean())
    brown_ratio = float(((r > g * 1.12) & (g > b * 1.05)).mean())
    dark_spot_ratio = float((brightness < 55).mean())

    metrics = {
        "green_ratio": round(green_ratio, 4),
        "brown_ratio": round(brown_ratio, 4),
        "dark_spot_ratio": round(dark_spot_ratio, 4),
        "brightness_mean": round(float(brightness.mean()), 2),
    }
    return metrics


def diagnose(metrics, symptoms):
    yellowing = 1.0 if symptoms.get("yellowing") else 0.0
    spots = 1.0 if symptoms.get("spots") else 0.0
    holes = 1.0 if symptoms.get("holes") else 0.0
    wilting = 1.0 if symptoms.get("wilting") else 0.0
    mold = 1.0 if symptoms.get("mold") else 0.0

    green_ratio = metrics["green_ratio"]
    brown_ratio = metrics["brown_ratio"]
    dark_spot_ratio = metrics["dark_spot_ratio"]

    scores = {
        "Healthy": 0.7 + green_ratio * 1.2 - brown_ratio * 0.8 - dark_spot_ratio * 0.7 - yellowing * 0.4,
        "Nitrogen deficiency": 0.3 + (1 - green_ratio) * 0.9 + yellowing * 1.3 + wilting * 0.2,
        "Fungal disease": 0.3 + dark_spot_ratio * 1.2 + spots * 1.1 + mold * 1.2,
        "Pest damage": 0.3 + holes * 1.4 + spots * 0.4 + brown_ratio * 0.3,
        "Drought stress": 0.3 + wilting * 1.2 + brown_ratio * 0.8 + (1 - green_ratio) * 0.5,
    }

    labels = list(scores.keys())
    probs = softmax([scores[k] for k in labels])
    results = [{"diagnosis": lbl, "probability": float(p)} for lbl, p in zip(labels, probs)]
    results.sort(key=lambda x: x["probability"], reverse=True)
    return results


RECOMMENDATIONS = {
    "Healthy": [
        "Continue standard scouting every 5-7 days.",
        "Maintain current irrigation and nutrient plan.",
    ],
    "Nitrogen deficiency": [
        "Apply split nitrogen feeding (small dose first).",
        "Check soil moisture before N application to improve uptake.",
    ],
    "Fungal disease": [
        "Inspect lower leaves and lesion spread in field samples.",
        "Plan fungicide treatment per crop stage and local regulations.",
    ],
    "Pest damage": [
        "Set field traps and inspect edge rows first.",
        "Use targeted insect control only after threshold confirmation.",
    ],
    "Drought stress": [
        "Adjust irrigation schedule and reduce stress window.",
        "Use anti-stress foliar support if compatible with crop stage.",
    ],
}

field_names, _ = field_names_and_features()
field_pick = st.selectbox("Field (optional)", ["No field"] + field_names, index=0)
event_field = "General" if field_pick == "No field" else field_pick

photo_source = st.radio("Photo source", ["Upload file", "Camera"], horizontal=True)
uploaded = None
if photo_source == "Upload file":
    uploaded = st.file_uploader("Photo (jpg/png)", type=["jpg", "jpeg", "png"], key="ai_photo_diag")
else:
    uploaded = st.camera_input("Take photo", key="ai_photo_diag_camera")

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    sym_yellowing = st.checkbox("Yellowing")
with c2:
    sym_spots = st.checkbox("Spots")
with c3:
    sym_holes = st.checkbox("Holes")
with c4:
    sym_wilting = st.checkbox("Wilting")
with c5:
    sym_mold = st.checkbox("Mold")

if uploaded:
    image = Image.open(uploaded)
    st.image(image, use_container_width=True)
    photo_name = getattr(uploaded, "name", "camera_photo.jpg")

    metrics = analyze_image(image)
    symptoms = {
        "yellowing": sym_yellowing,
        "spots": sym_spots,
        "holes": sym_holes,
        "wilting": sym_wilting,
        "mold": sym_mold,
    }

    results = diagnose(metrics, symptoms)
    top = results[0]

    st.subheader("Diagnosis probabilities")
    for item in results:
        st.progress(int(round(item["probability"] * 100)), text=f"{item['diagnosis']}: {item['probability']*100:.1f}%")

    st.subheader("Image metrics")
    st.json(metrics)

    st.subheader("Recommended actions")
    for rec in RECOMMENDATIONS.get(top["diagnosis"], []):
        st.write(f"- {rec}")

    payload = {
        "created_at": now_iso(),
        "field": None if field_pick == "No field" else field_pick,
        "top_diagnosis": top["diagnosis"],
        "top_probability": round(top["probability"], 4),
        "results": results,
        "metrics": metrics,
        "symptoms": symptoms,
        "filename": photo_name,
    }
    append_photo_diag(payload)

    add_event(
        field_name=event_field,
        event_type="photo_diagnosis",
        event_date=now_iso()[:10],
        note=f"{top['diagnosis']} ({top['probability']*100:.1f}%) from photo {photo_name}",
        source="ai_photo",
        meta={"metrics": metrics, "symptoms": symptoms},
    )

    st.success("Diagnosis saved to history and timeline.")
else:
    st.info("Upload a photo or use camera to run diagnosis.")
