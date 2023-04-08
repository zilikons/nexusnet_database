import streamlit as st
from py2neo import Graph, Node, Relationship, ServiceUnavailable

# Replace these with your Neo4j connection details
NEO4J_URI = st.secrets["NEO4J_URI"]
print(NEO4J_URI)
NEO4J_USER = st.secrets["NEO4J_USER"]
print(NEO4J_USER)
NEO4J_PASSWORD = st.secrets["NEO4J_PASSWORD"]
print(NEO4J_PASSWORD[3:])
try:
    graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    st.write("Connected to Neo4j")
except ServiceUnavailable as e:
    st.error(f"Failed to connect to Neo4j: {e}")
#graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def check_node_exists(label, properties):
    where_clause = " AND ".join([f"n.{key} = '{value}'" for key, value in properties.items()])

    query = f"MATCH (n:{label}) WHERE {where_clause} RETURN n LIMIT 1"
    result = graph.run(query).data()
    return len(result) > 0
def delete_all_nodes():
    graph.delete_all()
    return None
def create_project_node(project_info, coord_info):
    if check_node_exists('Project', project_info):
        raise Exception('Project already exists in the database')
    project_node = Node('Project', **project_info)
    if not check_node_exists('Researcher', coord_info):
        coord_node = Node('Researcher', **coord_info)
        graph.create(coord_node)
    else:
        coord_node = graph.nodes.match('Researcher', **coord_info).first()
    graph.create(project_node)
    relation = Relationship(coord_node, 'WORKS_ON', project_node, role='Project Coordinator')
    graph.create(relation)
    return None

def get_all_nodes():
    return graph.nodes.match().all()

def get_all_projects():
    return graph.nodes.match('Project').all()

def submit_project_info(name, proj_type, proj_website, proj_start, proj_end, coord, coord_contact, coord_host):
    project_dict = {'name': name, 'FundedBy': proj_type, 'Website': proj_website, 'StartDate': proj_start, 'EndDate': proj_end}
    coord_dict = {'name': coord, 'ContactMail': coord_contact, 'HostInstitution': coord_host}
    create_project_node(project_dict, coord_dict)
    return None

def create_case_study_node(case_study_info, case_study_lead_info, project_name):
    for key, value in case_study_info.items():
        if value == "" or value is None:
            case_study_info[key] = "None"
    if check_node_exists('CaseStudy', case_study_info):
        case_study_node = graph.nodes.match('CaseStudy', **case_study_info).first()
    else:
        case_study_node = Node('CaseStudy', **case_study_info)
        graph.create(case_study_node)
    if check_node_exists('Researcher', case_study_lead_info):
        case_study_lead_node = graph.nodes.match('Researcher', **case_study_lead_info).first()
    else:
        case_study_lead_node = Node('Researcher', **case_study_lead_info)
        graph.create(case_study_lead_node)
    project_node = graph.nodes.match('Project', name=project_name).first()
    cs_relation = Relationship(project_node, 'HAS_CASE_STUDY', case_study_node)
    researcher_relation = Relationship(case_study_lead_node, 'WORKS_ON', case_study_node, role='Case Study Leader')
    researcher_project_relation = Relationship(case_study_lead_node, 'WORKS_ON', project_node, role='Case Study Leader')
    graph.create(researcher_relation)
    graph.create(cs_relation)
    graph.create(researcher_project_relation)
    return None

st.title("NEXUSNET Database Survey Form")



selection = st.radio('Are you inputting a new project or adding a case study to an existing project?', ('New Project', 'New Case Study'))
if selection == 'New Project':
    with st.form(key='project_form'):
        name = st.text_input(label='Project Name')
        proj_type = st.selectbox(label='The project is funded by:',options=['HORIZON 2020', 'HORIZON EUROPE', 'Life','Prima','Interreg','Erasmus+','Marie Sklodowska-Curie', 'National/Regional Funding', 'Other'])
        proj_website = st.text_input(label='Project Website')
        coord = st.text_input(label='Project Coordinator')
        coord_contact = st.text_input(label='Project Coordinator Contact Email')
        coord_host = st.text_input(label='Project Coordinator Host Institution')
        proj_start = st.date_input(label='Project Start Date')
        proj_end = st.date_input(label='Project End Date')
        submit_button = st.form_submit_button(label='Submit Project Info')

    if submit_button:
        submit_project_info(name, proj_type, proj_website, proj_start,
                            proj_end, coord, coord_contact, coord_host)
        st.success('Project info submitted successfully!')

if selection == 'New Case Study':
    list_of_projects = [x['name'] for x in get_all_projects()]
    st.title("Case Study Form")

    # SECTION 2: Case Study characteristics
    st.header("Section 1: Case Study Characteristics")
    case_study_project = st.selectbox("1. Which project is the case study part of?", list_of_projects)
    st.subheader("WARNING: If you are adding a case study to a project that does not exist, please go back and create a new project first.")
    case_study_name = st.text_input("7. Name your case study")
    case_study_leader_institution = st.text_input("8. What is the host institution of the case study leader?")
    case_study_leader_name = st.text_input("Case study leader name")
    case_study_leader_contact = st.text_input("Case study leader email")
    case_study_country = st.text_input("9. In which country/countries is your case study located?")

    case_study_scale = st.selectbox(
        "10. What is the scale of the case study?",
        (
            "Global",
            "Continental",
            "International",
            "National",
            "State",
            "Regional",
            "Subregional",
            "River basin district",
            "Municipality/city",
            "Other (specify)",
        ),
    )
    case_study_scale_other = ""
    if case_study_scale == "Other (specify)":
        case_study_scale_other = st.text_input("Please specify:")

    case_study_transboundary = st.selectbox(
        "11. Is the case study transboundary?",
        ("No", "Transboundary between countries", "Transboundary between regions"),
    )

    case_study_objectives = st.text_area("12. What were/are the objectives (goals) of the case study?")

    # SECTION 3: Nexus components information
    st.header("Section 2: Nexus Components Information")

    nexus_sectors = st.multiselect(
        "13. What sectors are involved in the identified nexus challenges?",
        (
            "Water",
            "Food",
            "Energy",
            "Forestry",
            "Land Use / Land Availability",
            "Ecosystem and/or/Biodiversity",
            "Climate",
            "Soil",
            "Waste",
            "Health",
            "Other (specify)",
        ),
    )
    if "Other (specify)" in nexus_sectors:
        nexus_sectors_other = st.text_input("Please specify:")

    layers_of_analysis = st.multiselect(
        "14. Did the Case Study involve any workflows for the following layers of analysis?",
        (
            "Biophysical modeling",
            "Social",
            "Policy",
            "Economic",
            "Citizen science",
            "Gender dimension",
            "Metric development",
            "Other please specify:",
        ),
    )
    if "Other please specify:" in layers_of_analysis:
        layers_of_analysis_other = st.text_input("Please specify:")

    # SECTION 4: Modeling/Tools – Main simulation approaches and methodologies
    st.header("Section 3: Modeling/Tools – Main simulation approaches and methodologies")

    systems_analysis = st.selectbox(
        "15. Did you perform any Systems Analysis / Complexity Science?",
        ("YES", "NO"),
    )
    systems_analysis_specify = ""
    if systems_analysis == "YES":
        systems_analysis_specify = st.text_input("15a) If yes, please specify:")

    semantics_ontologies = st.selectbox(
        "16. Did you perform work on semantics and/or ontologies?",
        ("YES", "NO"),
    )
    semantics_ontologies_specify = ""
    if semantics_ontologies == "YES":
        semantics_ontologies_specify = st.text_input("16a) If yes, please specify:")

    footprint_calculations = st.selectbox(
        "17. Did you perform any footprint calculations (Water, Energy, Nexus, etc.)?",
        ("YES", "NO"),
    )
    footprint_calculations_specify = ""
    if footprint_calculations == "YES":
        footprint_calculations_specify = st.text_input("17a) If yes, please specify:")

    decision_support_system = st.selectbox(
    "18. Did you develop a Decision Support System?",
    ("YES", "NO"),
    )
    decision_support_system_details = ""
    if decision_support_system == "YES":
        decision_support_system_details = st.text_area("18a) If yes, please give more details:")

    ai_methodology = st.multiselect(
    "19. Did you use Artificial Intelligence methodology?",
    (
    "Knowledge Elicitation Engine",
    "Machine Learning",
    "Deep Learning",
    "Evolutionary Optimization Approaches",
    "SWORM",
    "Simulated Annealing",
    "Other (specify)",
    ),
    )
    if "Other (specify)" in ai_methodology:
        ai_methodology_other = st.text_input("Please specify:",key='ai_methodology_other')

    climate_projections = st.selectbox(
    "20. Did you perform climate projections (in years)?",
    ("YES", "NO"),
    )
    climate_projections_years = ""
    if climate_projections == "YES":
        climate_projections_years = st.selectbox(
    "20a) If yes, please specify:",
    ("30", "50", "100"),
    )

    existing_models = st.selectbox(
    "21. Did you use existing models for the projections?",
    ("YES", "NO"),
    )
    existing_models_specify = ""
    existing_models_adjustments = ""
    if existing_models == "YES":
        existing_models_specify = st.text_input("21a) If yes, please specify:")
    existing_models_adjustments = st.text_area("21b) Did you make any adjustments to the models specifically for the case studies?")

    nexus_indicators = st.selectbox(
    "22. Did you develop indicators/KPIs to assess the Nexus?",
    ("YES", "NO"),
    )
    nexus_indicators_specify = ""
    if nexus_indicators == "YES":
        nexus_indicators_specify = st.text_area("22a) If yes, please specify:")

    lifecycle_assessment = st.selectbox(
    "23. Did you perform Life Cycle Assessment?",
    ("YES", "NO"),
    )
    lifecycle_assessment_approach = ""
    if lifecycle_assessment == "YES":
        lifecycle_assessment_approach = st.text_input("23a) If yes, which approach did you use?")

    monitoring_techniques = st.multiselect(
    "24. Did you use any monitoring techniques (e.g. near real-time, or other)?",
    (
    "Sensors",
    "Satellite",
    "Citizen Science",
    "Crowd Sourcing",
    ),
    )
    st.header("Section 4: Stakeholder Engagement")

    stakeholders_involved = st.multiselect(
    "25. Which stakeholders are involved in the case study? (as part of the 5tuple helix)",
    (
    "Private sector/business (industry, business, enterprises)",
    "Governmental stakeholders/policy makers",
    "Academia/research",
    "Local citizens",
    "Other specify",
    ),
    )
    if "Other specify" in stakeholders_involved:
        stakeholders_involved_other = st.text_input("Please specify:")

    stakeholder_sectors = st.multiselect(
    "26. Which sector did the stakeholders belong to?",
    (
    "Agriculture",
    "Energy",
    "Water resources",
    "Tourism",
    "Farming",
    "Media",
    "Biodiversity and natural ecosystems",
    "Education",
    "Built environment/ construction",
    "Climate crisis/ civil protection",
    "Forestry",
    "Economics/Finance (banks, commerce, investors)",
    "Health",
    "Transport and logistic",
    "Culture",
    "Social Sciences and Humanities",
    "Other specify",
    ),
    )
    if "Other specify" in stakeholder_sectors:
        stakeholder_sectors_other = st.text_input("Please specify:")
    stakeholder_approach = st.multiselect(
        "27. Which approach did you use to engage the stakeholders?",
        (
            "Living Lab",
            "Stakeholder Mapping and engagement strategy",
            "Multi stakeholder forum",
            "Citizen Science",
            "Scenario building",
            "Community of Practice",
            "Co-creation",
            "Educational programs",
            "Informing stakeholders after tool development",
            "Training of local communities",
            "Other specify",
        ),
    )
    if "Other specify" in stakeholder_approach:
        stakeholder_approach_other = st.text_input("Please specify:")
    st.header("Section 5: Project Outputs")

    # Question 32
    visualization_options = {
        "a": "Dashboard",
        "b": "Decision support tools",
        "c": "Online market place",
        "d": "Augmented reality",
        "e": "Serious games",
        "f": "Training material",
        "g": "Virtual reality",
        "h": "Open access database",
        "i": "Other",
    }
    visualization_choice = st.selectbox("32. Did you develop any visualization of the results?", options=list(visualization_options.values()))
    visualization_key = [k for k, v in visualization_options.items() if v == visualization_choice][0]

    # Question 33
    sdg_assessment = st.selectbox("33. Did you perform any SDG's assessment?", ["YES", "NO"])

    # Question 34
    # Question 34
    if sdg_assessment == "YES":
        sdgs = [
            "SDG 1: No Poverty",
            "SDG 2: Zero Hunger",
            "SDG 3: Good Health and Well-being",
            "SDG 4: Quality Education",
            "SDG 5: Gender Equality",
            "SDG 6: Clean Water and Sanitation",
            "SDG 7: Affordable and Clean Energy",
            "SDG 8: Decent Work and Economic Growth",
            "SDG 9: Industry, Innovation, and Infrastructure",
            "SDG 10: Reduced Inequalities",
            "SDG 11: Sustainable Cities and Communities",
            "SDG 12: Responsible Consumption and Production",
            "SDG 13: Climate Action",
            "SDG 14: Life Below Water",
            "SDG 15: Life on Land",
            "SDG 16: Peace, Justice, and Strong Institutions",
            "SDG 17: Partnerships for the Goals",
        ]
        selected_sdgs = st.multiselect("34. If yes, please select which SDGs did you assess:", options=sdgs)


    # Question 35
    data_mgmt_plan = st.selectbox("35. Did you implement a Data Management Plan (e.g Knowledge Graph, dashboard)?", ["YES", "NO"])

    # Question 35a
    if data_mgmt_plan == 'YES':
        data_mgmt_plan_specify = st.text_input("35a. If yes, please specify:", key="35a")
    st.header("Section 6: Project After Life (Exploitation and Sustainability of the Solutions)")

    # Question 36
    outputs_options = {
        "a": "Creation of stakeholder networks",
        "b": "Teaching",
        "c": "Basis/ideas for a new scientific project",
        "d": "Citizen science platform/app",
        "e": "Serious game",
        "f": "Dashboard",
        "g": "Knowledge graph",
        "h": "Data inventory",
    }
    outputs_choice = st.multiselect("36. What kind of outputs did the case study develop?", options=list(outputs_options.values()))

    # Question 37
    usage_options = {
        "a": "For planning and management",
        "b": "For research purposes",
        "c": "For advancing the technology readiness level of solutions",
        "d": "For commercialization of solutions",
        "e": "For education purposes",
        "f": "For teaching purposes",
        "g": "The results have not been used so far but actions are being taken",
        "h": "The results are not used and there is no action in place to use them",
        "i": "Other purposes (please specify)",
    }
    usage_choice = st.selectbox("37. How have the outputs of the project been used?", options=list(usage_options.values()), key="usage_choice")

    if usage_choice == "Other purposes (please specify)":
        other_purpose = st.text_input("Please specify the other purpose:", key="other_purpose")

    # Question 38
    helix_categories = {
        "j": "Academia",
        "k": "Government",
        "l": "Industry",
        "m": "Civil society",
        "n": "Nature conservation organizations",
        "o": "Others (please specify)",
    }
    helix_choice = st.selectbox("38. When used, who used the results (Helix categorization)?", options=list(helix_categories.values()), key="helix_choice")

    if helix_choice == "Others (please specify)":
        other_helix = st.text_input("Please specify the other user:", key="other_helix")

    # Question 39
    impact_categories = {
        "1": "Scientific impact",
        "2": "Technological impact",
        "3": "Economic impact",
        "4": "Social impact",
        "5": "Political impact",
        "6": "Environmental impact",
        "7": "Health impact",
        "8": "Cultural impact",
        "9": "Training impacts",
    }
    selected_impacts = st.multiselect("39. Did the project have any/multiple of the following impacts? (Multiple choice answer possibility)", options=list(impact_categories.values()), key="impacts")

    # Question 40
    impact_description = st.text_area("40. Please briefly illustrate the impact(s) achieved:", key="impact_description")

    if st.button("Submit Case Study Data"):
        create_case_study_node({
            'name': case_study_name,
            'Country': case_study_country,
            'Scale': case_study_scale,
            'Transboundary': case_study_transboundary,
            'Objectives': case_study_objectives,
            'NexusSectors': nexus_sectors,
            'LayersOfAnalysis': layers_of_analysis,
            'SystemsAnalysis': systems_analysis_specify,
            'SemanticsOntologies': semantics_ontologies_specify,
            'FootprintCalcs': footprint_calculations_specify,
            'DecisionSupportSystems': decision_support_system_details,
            'AIMethodology': ai_methodology,
            'ClimateProjYears': climate_projections_years,
            'ExistingModels': existing_models_specify,
            'NexusIndicators': nexus_indicators_specify,
            'LifeCycleAssessment': lifecycle_assessment_approach,
            'MonitoringTechniques': monitoring_techniques,
            'Stakeholders': stakeholders_involved,
            'StakeholderSectors': stakeholder_sectors,
            'Visualization': visualization_choice,
            'SDGs': selected_sdgs,
            'CaseStudyOutputs': outputs_choice,
            'Usage': usage_choice,
            'Helix': helix_choice,
            'Impacts': selected_impacts,
            'ImpactDescription': impact_description,
        },
                               {
                'name':case_study_leader_name,
                'ContactMail':case_study_leader_contact,
                'HostInstitution':case_study_leader_institution,
        },
                case_study_project)
        st.success("Case Study Data Submitted Successfully!")






# label = st.text_input("Node label")
# property_key = st.text_input("Property key")
# property_value = st.text_input("Property value")

# if st.button("Create Node"):
#     node_properties = {property_key: property_value}
#     create_node(label, node_properties)
#     st.success("Node created successfully")



if st.button("Delete All Data"):
    delete_all_nodes()
    st.success("All data nodes deleted successfully")
st.header("All Data Nodes")
all_nodes = get_all_nodes()
for node in all_nodes:
    st.write(node)
