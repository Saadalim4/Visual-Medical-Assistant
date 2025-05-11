import streamlit as st
from PIL import Image
import base64
import requests
from groq_api_key import groq_api_key  # Ensure this file exists or replace with your key directly
from deep_translator import GoogleTranslator
import io
import re

# ========== Medical Glossary ========== #
medical_glossary = {
    "cerebral atrophy": "Shrinkage or loss of brain cells, often related to aging or diseases like Alzheimer’s.",
    "lesion": "An area of abnormal tissue, which could be caused by disease or injury.",
    "infarct": "Tissue death due to lack of blood supply, often seen in strokes.",
    "edema": "Swelling caused by excess fluid trapped in tissues.",
    "hemorrhage": "Excessive bleeding, either inside or outside the body.",
    "calcification": "Build-up of calcium in body tissues, often hardening them.",
    "contrast enhancement": "Technique using contrast agents in imaging to highlight areas, often related to inflammation or tumors.",
    "ventricular dilation": "Enlargement of the brain's ventricles, may suggest hydrocephalus or brain atrophy.",
    "mass effect": "Pressure from a mass (like a tumor) displacing surrounding brain structures.",
    "midline shift": "A shift of brain structures from their normal position, usually due to swelling or mass."
}

# ========== Emergency Keywords ========== #
emergency_keywords = ["hemorrhage", "infarct", "mass effect", "midline shift", "severe edema"]

# ========== Medication Dictionary ========== #
medication_dict = {
    "cerebral atrophy": "Donepezil, Memantine (for Alzheimer's related cases)",
    "lesion": "Corticosteroids (for inflammation), Surgery (if malignant)",
    "infarct": "Aspirin, Clopidogrel, or Anticoagulants (for ischemic strokes)",
    "edema": "Diuretics (e.g., Furosemide), corticosteroids",
    "hemorrhage": "Blood pressure medication, Surgery, Coagulation therapy",
    "calcification": "Calcium channel blockers, Surgery (in some cases)",
    "contrast enhancement": "Consult with oncologist or neurologist, depending on the findings",
    "ventricular dilation": "Diuretics, Surgery (for hydrocephalus)",
    "mass effect": "Surgery, Chemotherapy, Radiation (depending on tumor type)",
    "midline shift": "Surgical intervention, Decompression procedures"
}

# ========== Explanation Function ========== #
def highlight_and_explain_terms(text):
    explanations = {}
    lower_text = text.lower()
    for term in medical_glossary:
        if term in lower_text:
            explanations[term] = medical_glossary[term]
    return explanations

# ========== Emergency Detection ========== #
def check_for_emergency(text):
    detected_keywords = []
    lower_text = text.lower()
    for keyword in emergency_keywords:
        if keyword in lower_text:
            detected_keywords.append(keyword)
    return detected_keywords

# ========== OCR Extraction (Fixed) ========== #
def extract_text_from_base64_image(base64_img):
    url = "https://api.ocr.space/parse/image"
    payload = {
        'base64Image': 'data:image/png;base64,' + base64_img,
        'language': 'eng',
        'isOverlayRequired': False,
        'apikey': 'K88392357288957'  # Use your own API key here
    }
    response = requests.post(url, data=payload)
    result = response.json()

    try:
        parsed_results = result.get("ParsedResults")
        if parsed_results and len(parsed_results) > 0:
            return parsed_results[0].get("ParsedText", "").strip()
        else:
            return "❌ OCR did not detect any readable text in the image. Please upload a clearer image."
    except Exception as e:
        return f"❌ OCR failed with error: {str(e)}"

# ========== Encode Image to Base64 ========== #
def encode_image(image_file):
    return base64.b64encode(image_file.read()).decode("utf-8")

# ========== LLM Generation (Groq API) ========== #
def generate_response_groq(text, language='English'):
    prompt = f"Please analyze the following medical image description and provide insights in {language}:\n\n{text}"
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
          "Authorization": f"Bearer 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",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=payload)
    response_json = response.json()
    if 'choices' in response_json:
        return response_json['choices'][0]['message']['content']
    else:
        st.error(f"Unexpected response format: {response_json}")
        return "❌ Analysis failed due to an unexpected response from the API."

# ========== Translation ========== #
def translate_response(text, target_language):
    if target_language.lower() == "hindi":
        try:
            return GoogleTranslator(source='auto', target='hi').translate(text)
        except Exception as e:
            st.error(f"Translation failed: {e}")
            return text
    return text

# ========== Streamlit UI ========== #
st.set_page_config(page_title="Visual Medical Assistant", page_icon="🩺", layout="wide")
st.title("Visual Medical Assistant 👨‍⚕️ 🩺 🏥")
st.subheader("An app to help with medical image analysis")

# Language Selection
language = st.radio("Choose language for analysis:", ["English", "Hindi"])

# Upload Image
file_uploaded = st.file_uploader('Upload the medical image (MRI/CT/Scan)', type=['png', 'jpg', 'jpeg'])

if file_uploaded:
    st.image(file_uploaded, width=300, caption="Uploaded Image")
    submit = st.button("Generate Analysis")

    if submit:
        with st.spinner("Analyzing the image..."):
            try:
                base64_img = encode_image(file_uploaded)
                image_text = extract_text_from_base64_image(base64_img)

                if image_text.startswith("❌"):
                    st.error(image_text)
                else:
                    # Truncate if needed
                    MAX_CHARS = 3000
                    if len(image_text) > MAX_CHARS:
                        image_text = image_text[:MAX_CHARS] + "\n\n[Text truncated for model input]"

                    # Generate LLM response
                    response_text = generate_response_groq(image_text, language=language)
                    final_output = translate_response(response_text, language)

                    # Show results
                    st.markdown("### 🧾 Analysis Report")
                    st.write(final_output)

                    # Emergency detection
                    emergency_findings = check_for_emergency(final_output)
                    if emergency_findings:
                        st.error("🚨 Emergency Alert Detected!")
                        st.warning(f"Critical findings: {', '.join(emergency_findings).capitalize()}")
                        st.info("👉 Please contact an emergency medical service immediately.\n\n**Helplines:**  \n- 108 (Ambulance)  \n- 112 (Emergency)")

                    # Medication suggestions
                    prescribed_meds = []
                    for term in medical_glossary:
                        if term in final_output.lower():
                            prescribed_meds.append(medication_dict.get(term))

                    if prescribed_meds:
                        st.markdown("### 💊 Suggested Medications")
                        for meds in prescribed_meds:
                            st.write(f"- {meds}")
                    else:
                        st.info("No medications suggested based on the findings.")

                    # Glossary
                    st.markdown("---")
                    st.markdown("### 🧠 Medical Term Explanations")
                    explanations = highlight_and_explain_terms(image_text)

                    if explanations:
                        for term, definition in explanations.items():
                            st.markdown(f"**{term.capitalize()}**: {definition}")
                    else:
                        st.info("No complex medical terms found for explanation.")

            except Exception as e:
                st.error(f"❌ Error occurred: {str(e)}")
