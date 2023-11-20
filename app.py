import streamlit as st
import pandas as pd
import uuid
from neo4j import GraphDatabase, basic_auth

# Replace these with your Neo4j connection details
uri = st.secrets['NEO4J_URI']
user = st.secrets['NEO4J_USER']
password = st.secrets['NEO4J_PASSWORD']

driver = GraphDatabase.driver(uri, auth=basic_auth(user, password))

def validate_lat_lon(lat, lon):
    # Check if the values are floats
    try:
        lat = float(lat)
        lon = float(lon)
    except ValueError:
        return False

    # Check if the values are within valid ranges
    if lat < -90 or lat > 90:
        return False
    if lon < -180 or lon > 180:
        return False

    return True

def run_query(query, parameters=None):
    with driver.session() as session:
        return session.run(query, parameters).data()


def delete_all_nodes():
    query = "MATCH (n) DETACH DELETE n"
    run_query(query)
    return None
def create_project_node(project_info, coord_info):
    project_name = project_info['name']
    if check_project_exists_with_same_name(project_name):
        raise Exception('Project with the same name already exists in the database')

    query = """
    MERGE (coord:Institution {name: $coord_info.name})
    ON CREATE SET coord += $coord_info, coord.id = apoc.create.uuid()
    CREATE (project:Project $project_info)
    MERGE (coord)-[r:WORKS_ON {role: 'Project Coordinator'}]->(project)
    ON CREATE SET r.timestamp = timestamp()

    """
    run_query(query, {'coord_info': coord_info, 'project_info': project_info})

    return None

def check_project_exists_with_same_name(project_name):
    query = f"MATCH (n:Project) WHERE n.name = '{project_name}' RETURN n LIMIT 1"
    result = run_query(query)
    return len(result) > 0


def check_node_exists(label, properties):
    where_clause = " AND ".join([f"n.{key} = '{value}'" for key, value in properties.items()])
    query = f"MATCH (n:{label}) WHERE {where_clause} RETURN n LIMIT 1"
    result = run_query(query)
    return len(result) > 0

def generate_unique_project_id():
    # You can implement your own logic to generate a unique project ID
    return str(uuid.uuid4())

def get_all_nodes():
    query = "MATCH (n) RETURN n"
    return run_query(query)

def get_all_projects():
    query = "MATCH (n:Project) RETURN n"
    return run_query(query)

def submit_project_info(name, proj_type, proj_website, proj_funding, proj_start, proj_end, coord_host):
    project_dict = {'name': name, 'FundedBy': proj_type, 'Website': proj_website, 'FundingAmount': proj_funding, 'StartDate': proj_start, 'EndDate': proj_end}
    coord_dict = {'name': coord_host}
    create_project_node(project_dict, coord_dict)
    return None

def create_case_study_node(case_study_info, case_study_lead_info, project_name, case_study_leader_host_institution):
    for key, value in case_study_info.items():
        if value == "" or value == [] or value is None:
            case_study_info[key] = "Not Available"
    query = """
    CREATE (case_study:CaseStudy)
        SET case_study.id = apoc.create.uuid(), case_study += $case_study_info
    MERGE (lead:Researcher {name: $case_study_lead_info.name})
        ON CREATE SET lead.id = apoc.create.uuid(), lead += $case_study_lead_info
    MERGE (institution:Institution {name: $case_study_leader_host_institution})
        ON CREATE SET institution.id = apoc.create.uuid()
    WITH case_study, lead, institution
    MATCH (project:Project {name: $project_name})
    MERGE (project)-[:HAS_CASE_STUDY]->(case_study)
    MERGE (lead)-[r1:WORKS_ON {role: 'Case Study Leader'}]->(case_study)
        ON CREATE SET r1.timestamp = timestamp()
    MERGE (lead)-[r2:WORKS_ON {role: 'Case Study Leader'}]->(project)
        ON CREATE SET r2.timestamp = timestamp()
    MERGE (lead)-[:BELONGS_TO]->(institution)
    """

    run_query(query, {
        'case_study_info': case_study_info,
        'case_study_lead_info': case_study_lead_info,
        'project_name': project_name,
        'case_study_leader_host_institution': case_study_leader_host_institution
    })
    return None


def get_all_node_labels():
    query = """
    CALL db.labels()
    YIELD label
    RETURN label
    """
    results =  run_query(query)
    labels = []
    for result in results:
        labels.append(result['label'])
    return labels

def get_all_node_names_of_label(label):
    query = f"""
    MATCH (n:{label})
    RETURN n.name
    """
    results = run_query(query)
    names = []
    for result in results:
        names.append(result['n.name'])
    return names

def get_node_info(label,name):
    query=f"""
    MATCH (n:{label} {{name: '{name}'}})
    RETURN n
    """
    result = run_query(query)
    return list(result[0]['n'].keys())

def modify_node_attribute(label,name,attribute,new_value):
    query=f"""
    MATCH (n:{label} {{name: '{name}'}})
    SET n.{attribute} = '{new_value}'
    """
    run_query(query)
    return None

def fetch_project_data(project_name,project_type):
    name = project_name.lower()
    if project_type == 'HORIZON EUROPE':
        df = pd.read_csv('data/horizon_europe_c.csv')
    else:
        df = pd.read_csv('data/horizon_2020_c.csv')
    df = df[df['projectAcronym'].str.lower() == name]
    return df

st.title("NEXUSNET Database Survey Form")
st.header("Introduction")
st.text("""Thank you for adding your Case Study information to the Global Nexus Case Studies Platform. \n
The platform is a free-to-access tool that hosts Nexus Case Studies from all around the world held by Cost Action NEXUSNET and supported by Nexus Cluster Project. \n
The platform allows the users to visualize the information of each Case Studies based on multiple queries and also download a factsheet with complete information of each CS. \n
You will now be guided to provide information about your CS.
""")
selection = st.radio('Are you inputting a new project or adding a case study to an existing project?', ('New Project', 'New Case Study'))
if selection == 'New Project':
    name = st.text_input(label='Project Name')
    proj_type = st.selectbox(label='The project is funded by:',options=['HORIZON 2020', 'HORIZON EUROPE', 'ERC', 'Life','Prima','Interreg','Erasmus+','Marie Sklodowska-Curie', 'National/Regional Funding', 'Other'], index=1)
    coord_host = st.text_input(label='Project Coordinator Host Institution')
    proj_website = st.text_input(label='Project Website')
    proj_funding = st.text_input(label='Project Funding Amount')
    proj_start = st.date_input(label='Project Start Date')
    proj_end = st.date_input(label='Project End Date')
    submit_button = st.button(label='Submit Project Info')

    if submit_button:
        submit_project_info(name, proj_type, proj_website, proj_funding, proj_start,
                            proj_end, coord_host)
        st.success('Project info submitted successfully!')

if selection == 'New Case Study':
    list_of_projects = [x['n']['name'] for x in get_all_projects()]
    st.title("Case Study Form")

    # SECTION 2: Case Study characteristics
    st.header("Section 1: Case Study Characteristics")
    case_study_project = st.selectbox("Which project is the case study part of?", list_of_projects)
    st.subheader(":exclamation: :red[WARNING] :exclamation: : If you are adding a case study to a project that does not exist, please go back and create a new project first.")
    case_study_name = st.text_input("Name your case study", key="case_study_name")
    case_study_leader_institution = st.text_input("What is the host institution of the case study leader?", key="case_study_leader_institution")
    case_study_leader_name = st.text_input("Case study leader name", key="case_study_leader_name")
    case_study_leader_contact = st.text_input("Case study leader email", key="case_study_leader_contact")
    case_study_country = st.text_input("In which country/countries is your case study located?", key="case_study_country")
    #case_study_latitude = st.text_input("9c. What is the latitude of the case study?",value=0.0)
    #case_study_longitude = st.text_input("9b. What is the longitude of the case study?",value=0.0)
    #if validate_lat_lon(case_study_latitude, case_study_longitude):
    #    st.write("Valid latitude and longitude values")
    #else:
    #    st.write("Invalid latitude and longitude values")

    case_study_scale = st.selectbox(
        "What is the scale of the case study?",
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
        case_study_scale_other = st.text_input("Please specify:", key="case_study_scale_other")

    case_study_transboundary = st.selectbox(
        "Is the case study transboundary?",
        ("No", "Transboundary between countries", "Transboundary between regions"),
    )

    case_study_objectives = st.text_area("What were/are the objectives (goals) of the case study?", key="case_study_objectives")

    # SECTION 2: Nexus components information
    st.header("Section 2: Nexus Components Information")

    nexus_sectors = st.multiselect(
        "What sectors are involved in the identified nexus challenges?",
        (
            "Water",
            "Food",
            "Energy",
            "Land Use / Land Availability",
            "Ecosystem and/or/Biodiversity",
            "Climate",
            "Soil",
            "Waste",
            "Health",
            "Other (please specify)",
        ),
    )
    nexus_sectors_other = ""
    if "Other (please specify)" in nexus_sectors:
        nexus_sectors_other = st.text_input("Please specify:", key="nexus_sectors_other")

    layers_of_analysis = st.multiselect(
        "What are the main areas of investigation for research in the CS?",
        (
            "Biophysical modeling",
            "Behavioural studies and stakeholder perception",
            "Governance and policy",
            "Economic",
            "Other (please specify):",
        ),
    )
    layers_of_analysis_other = ""
    if "Other (please specify):" in layers_of_analysis:
        layers_of_analysis_other = st.text_input("Please specify:", key="layers_of_analysis_other")

    # SECTION 4: Modeling/Tools – Main simulation approaches and methodologies
    st.header("Section 3: Modeling/Tools - Main simulation approaches and methodologies")

    systems_analysis = st.multiselect(
        "Systems analysis: Which of the following method(s) have you used?",
        ("System Dynamics Modelling (SDM)",
         "Multi-sectoral systems analysis",
         "Material flows analysis",
         "System informatics and analytics",
         "Causal loop diagrams and system feedbacks",
         "Mathematical/engineering modeling",
         "Resource flows",
         "Network analysis",
         "Other (please specify)"),
    )
    systems_analysis_specify = ""
    if "Other (please specify)" in systems_analysis:
        systems_analysis_specify = st.text_input("Please specify:", key="systems_analysis_specify")
    #added
    integrated_modeling = st.multiselect(
        "Integrated modelling: Which of the following method(s) have you used?",
        ("SWAT (Soil and Water Assessment Tool)",
         "CLEWS model (Climate, Land, Energy and Water Strategies)",
         "SEWEM (System-Wide Economic-Water-Energy Model)",
         "WEF Nexus tool 2.0",
         "PRIMA (Platform for Regional Integrated Modeling and Analysis)",
         "MCDA (Multi-Criteria Decision Analysis)",
         "MuSIASEM (Multi-scale Integrated Analysis of Societal and Ecosystem Metabolism)",
         "Integrated assessment models",
         "Other (please specify)")
    )
    #added
    integrated_modeling_specify = ""
    if "Other (please specify)" in integrated_modeling:
        integrated_modeling_specify = st.text_input("Please specify:", key="integrated_modeling_specify")
    #added
    environmental_management = st.multiselect(
        "Environmental management: Which of the following method(s) have you used?",
        ("Scenario analysis",
         "Footprinting",
         "Life Cycle Assessment",
         "Decision Support System",
         "Other (please specify)")
    )
    #added
    environmental_management_specify = ""
    if "Other (please specify)" in environmental_management:
        environmental_management_specify = st.text_input("Please specify:", key="environmental_management_specify")
    #added
    economics = st.multiselect(
        "Economics: Which of the following method(s) have you used?",
        ("Cost-benefit analysis",
         "Input-output analysis",
         "Trade-off/Synergy analysis",
         "Social accounting matrix",
         "Value chain analysis",
         "Supply chain analysis",
         "Economic modelling",
         "Other (please specify)")
    )
    #added
    economics_specify = ""
    if "Other (please specify)" in economics:
        economics_specify = st.text_input("Please specify:", key="economics_specify")
    #added
    statistics = st.multiselect(
        "Statistics: Which of the following method(s) have you used?",
        ("Principal component analysis",
         "Regression statistics",
         "Trend analysis",
         "Data mining",
         "Other (please specify)")
    )
    #added
    statistics_specify = ""
    if "Other (please specify)" in statistics:
        statistics_specify = st.text_input("Please specify:", key="statistics_specify")
    #added
    social_science = st.multiselect(
        "Social science: Which of the following method(s) have you used?",
        ("Institutional analysis",
         "Questionnaires, surveys or interviews",
         "Historical analysis",
         "Agent-based modelling",
         "Delphi technique",
         "Critical discourse analysis",
         "Stakeholder analysis",
         "Participatory workshops/focus groups",
         "Living labs",
         "Policy analysis",
         "Other (please specify)")
    )
    #added
    social_science_specify = ""
    if "Other (please specify)" in social_science:
        social_science_specify = st.text_input("Please specify:", key="social_science_specify")

    semantics_ontologies = st.selectbox(
        "Did you perform work on ontology engineering?",
        ("YES", "NO"),
    )
    semantics_ontologies_specify = ""
    if semantics_ontologies == "YES":
        semantics_ontologies_specify = st.text_input("If yes, please specify:", key="semantics_ontologies_specify")

    footprint_calculations = st.selectbox(
        "Did you perform any footprint calculations (Water, Energy, Nexus, etc.)?",
        ("YES", "NO"),
    )
    footprint_calculations_specify = ""
    if footprint_calculations == "YES":
        footprint_calculations_specify = st.text_input("If yes, please specify:", key="footprint_calculations_specify")

    decision_support_system = st.selectbox(
    "Did you develop a Decision Support System?",
    ("YES", "NO"),
    )
    decision_support_system_details = ""
    if decision_support_system == "YES":
        decision_support_system_details = st.text_area("If yes, please give more details:", key="decision_support_system_details")
    #added
    climate_projections = st.multiselect(
        "Climate projections: Which of the following model(s) have you used?",
        ("CAPRI",
         "MAGPIE",
         "E3ME",
         "MAGNET",
         "GLOBIO",
         "SWAT",
         "HYDROSIM",
         "UWOT",
         "WEAP",
         "LEAP",
         "Other (please specify)")
    )
    #added
    climate_projections_specify = ""
    if "Other (please specify)" in climate_projections:
        climate_projections_specify = st.text_input("Please specify:", key="climate_projections_specify")
    #added
    data_types = st.multiselect(
        "Data types: Which of the following data sources have you used?",
        ("Lab test outputs",
         "Field test outputs",
         "Sensors",
         "Literature",
         "Model outputs",
         "Qualitative",
         "Publicly available platforms (OECD, FAO, EUROSTAT)",
         "National statistics",
         "Other (please specify)")
    )
    #added
    data_types_specify = ""
    if "Other (please specify)" in data_types:
        data_types_specify = st.text_input("Please specify:", key="data_types_specify")
    #added
    ai_methodology = st.multiselect(
    "Did you use Artificial Intelligence methodology?",
    (
    "Knowledge Elicitation Engine",
    "Machine Learning",
    "Deep Learning",
    "Evolutionary Optimization Approaches",
    "SWORM",
    "Simulated Annealing",
    "Agent Based Modeling",
    "Other (specify)",
    ),
    )
    ai_methodology_other = ""
    if "Other (specify)" in ai_methodology:
        ai_methodology_other = st.text_input("Please specify:",key='ai_methodology_other')
    nexus_indicators = st.selectbox(
    "Did you develop indicators/KPIs to assess the Nexus?",
    ("YES", "NO"),
    )
    nexus_indicators_specify = ""
    if nexus_indicators == "YES":
        nexus_indicators_specify = st.text_area("If yes, please specify:", key="nexus_indicators_specify")
    monitoring_techniques = st.multiselect(
    "Did you use any monitoring techniques (e.g. near real-time, or other)?",
    (
    "Sensors",
    "Satellite",
    "Citizen Science",
    "Crowd Sourcing",
    "Web-scraping tools",
    "Field visits/sampling",
    "Other (please specify)"
    ),
    )
    #added
    monitoring_techniques_specify = ""
    if "Other (please specify)" in monitoring_techniques:
        monitoring_techniques_specify = st.text_input("Please specify:", key="monitoring_techniques_specify")
    st.header("Section 4: Stakeholder Engagement")

    stakeholders_involved = st.multiselect(
    "Which stakeholders are involved in the case study? (as part of the 5tuple helix)",
    (
    "Private sector/business (industry, business, enterprises)",
    "Governmental stakeholders/policy makers",
    "Academia/research",
    "Local citizens",
    "Other (please specify)",
    ),
    )
    stakeholders_involved_other = ""
    if "Other (please specify)" in stakeholders_involved:
        stakeholders_involved_other = st.text_input("Please specify:", key="stakeholders_involved_other")

    stakeholder_sectors = st.multiselect(
    "Which sector did the stakeholders belong to?",
    (
    "Agriculture/Farming",
    "Energy",
    "Water resources",
    "Tourism",
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
    "Other (please specify)",
    ),
    )
    stakeholder_sectors_other = ""
    if "Other (please specify)" in stakeholder_sectors:
        stakeholder_sectors_other = st.text_input("Please specify:", key="stakeholder_sectors_other")
    stakeholder_approach = st.multiselect(
        "Which approach did you use to engage the stakeholders?",
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
            "Other (please specify)",
        ),
    )
    stakeholder_approach_other = ""
    if "Other (please specify)" in stakeholder_approach:
        stakeholder_approach_other = st.text_input("Please specify:", key="stakeholder_approach_other")
    #added
    biggest_org = st.text_input("Which organization is/was the biggest actor affecting other organizations in the nexus?", key="biggest_org")
    #added
    biggest_org_sector = st.multiselect(
        "Which sector did the biggest organization belong to?",
        ("Water",
         "Energy",
         "Food",
         "Ecosystems",
         "Other")
    )
    biggest_org_sector_other = ""
    if "Other" in biggest_org_sector:
        biggest_org_sector_other = st.text_input("Please specify:", key="biggest_org_sector_other")
    #added
    biggest_org_engaged = st.selectbox("Is this organization engaged in the project?",
                                       ("YES", "NO"))
    #added
    st.header("Section 5: Governance and Policy")
    #added
    governance_assessment = st.selectbox("Did you perform any governance assessment?",
                                         ("YES", "NO"))
    #added
    governance_assessment_specify = ""
    if governance_assessment == "YES":
        governance_assessment_specify = st.text_input("If yes, please specify:",key = "governance_assessment_specify")
    #added
    policy_coherence_assessment = st.selectbox("Did you perform any Policy Coherence Assessment to identify policy gaps?",
        ("YES", "NO"))
    #added
    policy_coherence_assessment_specify = ""
    if policy_coherence_assessment == "YES":
        policy_coherence_assessment_specify = st.text_input("If yes, please specify:",key = "policy_coherence_assessment_specify")
    #added
    important_drivers = st.multiselect(
        "What are the most important drivers underpinning the Nexus challenges investigated?",
        ("Governance",
         "Technological",
         "Cultural",
         "Socio-economic",
         "Biophysical",
         "Other (please specify)")
    )
    #added
    important_drivers_specify = ""
    if "Other (please specify)" in important_drivers:
        important_drivers_specify = st.text_input("Please specify:", key = "important_drivers_specify")
    #added
    policy_coproduction = st.selectbox(
        "What was the level of co-production of policy solutions and recommendations?",
        ("Solutions were derived by the research team",
         "Solutions were derived by the research team and validated by stakeholders",
         "Solutions were derived bottom-up by stakeholders",
        )
    )
    #added
    current_implementation = st.selectbox(
        "Are the solutions and recommendations currently being implemented?",
        ("All solutions and recommendations have been implemented",
         "Some solutions and recommendations have been implemented",
         "None of the solutions and recommendations have been implemented",
    )
    )
    #added
    solutions_financing = st.selectbox(
        "How were the solutions and recommendations financed?",
        ("Public funding",
         "Private funding",
         "Public-private funding",
         "Other (please specify)")
    )
    #added
    solutions_financing_specify = ""
    if "Other (please specify)" in solutions_financing:
        solutions_financing_specify = st.text_input("Please specify:", key = "solutions_financing_specify")
    #added
    governance_challenges = st.text_area("What are the main governance challenges in relation to nexus that you faced in the case study?", key = "governance_challenges")
    #added
    governance_lessons = st.text_area("What are the main lessons learned in relation to governance and nexus?", key = "governance_lessons")
    st.header("Section 6: Project Outputs")

    # Question 32
    visualization_options = {
        "a": "Dashboard",
        "b": "Decision support tools",
        "c": "Online market place",
        "d": "Augmented reality/Virtual reality",
        "e": "Serious games",
        "f": "Training material",
        "g": "Open access database",
        "h": "Mobile/tablet application",
        "i": "Other (please specify)",
    }
    visualization_choice = st.multiselect("Did you develop any visualization of the results?",
                                          (list(visualization_options.values())))
    visualization_choice_other = ""
    if "Other (please specify)" in visualization_choice:
        visualization_choice_other = st.text_input("Please specify:", key="visualization_choice_other")
    # Question 33
    sdg_assessment = st.selectbox("Did you perform any SDG's assessment?", ["YES", "NO"])

    # Question 34
    selected_sdgs = ""
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

        selected_sdgs = st.multiselect("If yes, please select which SDGs did you assess:", options=sdgs)
    #added
        sdg_assessment_method = st.text_input("What was the method used for SDG assessment?", key = "sdg_assessment_method")
    # Question 35
    data_mgmt_plan = st.selectbox("Did you implement a Data Management Plan (e.g Knowledge Graph, dashboard)?", ["YES", "NO"])

    # Question 35a
    data_mgmt_plan_specify = ""
    if data_mgmt_plan == 'YES':
        data_mgmt_plan_specify = st.text_input("If yes, please specify:", key="data_mgmt_plan_specify")
    st.header("Section 7: Project After Life (Exploitation and Sustainability of the Solutions)")

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
    outputs_choice = st.multiselect("What kind of outputs did the case study develop?", options=list(outputs_options.values()))

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
    usage_choice = st.multiselect("How have the outputs of the project been used?", options=list(usage_options.values()), key="usage_choice")

    usage_other_purpose = ""
    if "Other purposes (please specify)" in usage_choice:
        usage_other_purpose = st.text_input("Please specify the other purpose:", key="other_purpose")

    # Question 38
    helix_categories = {
        "j": "Academia",
        "k": "Government",
        "l": "Industry",
        "m": "Civil society",
        "n": "Nature conservation organizations",
        "o": "Others (please specify)",
    }
    helix_choice = st.multiselect("When used, who used the results (Helix categorization)?", options=list(helix_categories.values()), key="helix_choice")

    other_helix = ""
    if "Others (please specify)" in helix_choice:
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
    selected_impacts = st.multiselect("Did the project have any/multiple of the following impacts?", options=list(impact_categories.values()), key="impacts")

    # Question 40
    impact_description = st.text_area("Please briefly illustrate the impact(s) achieved:", key="impact_description")

    if st.button("Submit Case Study Data"):
        case_study_data_specify = {
            'case_study_scale_other':case_study_scale_other,
            'nexus_sectors_other':nexus_sectors_other,
            'layers_of_analysis_other':layers_of_analysis_other,
            'systems_analysis_specify':systems_analysis_specify,
            'integrated_modeling_specify':integrated_modeling_specify,
            'environmental_management_specify':environmental_management_specify,
            'economics_specify':economics_specify,
            'statistics_specify':statistics_specify,
            'social_science_specify':social_science_specify,
            'climate_projections_specify':climate_projections_specify,
            'semantics_ontologies_specify':semantics_ontologies_specify,
            'footprint_calculations_specify':footprint_calculations_specify,
            'decision_support_system_details':decision_support_system_details,
            'data_types_specify':data_types_specify,
            'ai_methodology_other':ai_methodology_other,
            'nexus_indicators_specify':nexus_indicators_specify,
            'monitoring_techniques_specify':monitoring_techniques_specify,
            'stakeholders_involved_other':stakeholders_involved_other,
            'stakeholder_sectors_other':stakeholder_sectors_other,
            'stakeholder_approach_other':stakeholder_approach_other,
            'biggest_org_sector_other':biggest_org_sector_other,
            'governance_assessment_specify':governance_assessment_specify,
            'policy_coherence_assessment_specify':policy_coherence_assessment_specify,
            'important_drivers_specify':important_drivers_specify,
            'solutions_financing_specify':solutions_financing_specify,
            'visualization_choice_other':visualization_choice_other,
            'data_mgmt_plan_specify':data_mgmt_plan_specify,
            'usage_other_purpose':usage_other_purpose,
            'other_helix':other_helix,
        }
        case_study_data = {
            'name': case_study_name,
            'Country': case_study_country,
            #'latitude':case_study_latitude,
            #'longitude':case_study_longitude,
            'Scale': case_study_scale,
            'Transboundary': case_study_transboundary,
            'Objectives': case_study_objectives,
            'NexusSectors': nexus_sectors,
            'LayersOfAnalysis': layers_of_analysis,
            'SystemsAnalysis': systems_analysis_specify,
            'IntegratedModeling': integrated_modeling,
            'EnvironmentalManagement': environmental_management,
            'Economics': economics,
            'Statistics': statistics,
            'SocialScience': social_science,
            'ClimateProjections': climate_projections,
            'DataTypes': data_types,
            'AIMethodology': ai_methodology,
            #'ClimateProjYears': climate_projections_years,
            #'ExistingModels': existing_models_specify,
            #'LifeCycleAssessment': lifecycle_assessment_approach,
            'MonitoringTechniques': monitoring_techniques,
            'Stakeholders': stakeholders_involved,
            'StakeholderSectors': stakeholder_sectors,
            'StakeholderApproach': stakeholder_approach,
            'ImportantDrivers': important_drivers,
            'SolutionsFinancing': solutions_financing,
            'GovernanceChallenges': governance_challenges,
            'GovernanceLessons': governance_lessons,
            'MostImpactfulOrg': biggest_org,
            'MostImpactfulOrgSector': biggest_org_sector,
            'MostImpactfulOrgEngaged': biggest_org_engaged,
            'Visualization': visualization_choice,
            'SDGs': selected_sdgs,
            'CaseStudyOutputs': outputs_choice,
            'Usage': usage_choice,
            'Helix': helix_choice,
            'Impacts': selected_impacts,
            'ImpactDescription': impact_description,
            'PolicyCoProduction': policy_coproduction,
            'CurrentImplementation': current_implementation
        }
        for key, value in case_study_data_specify.items():
            if value:
                case_study_data[key] = value
        case_study_leader_data = {
                'name':case_study_leader_name,
                'ContactMail':case_study_leader_contact,
                'HostInstitution':case_study_leader_institution,
        }
        create_case_study_node(case_study_data,
                               case_study_leader_data,
        case_study_project, case_study_leader_institution)
        st.success("Case Study Data Submitted Successfully!")

# if selection == "Modify Nodes":
#     labels = get_all_node_labels()
#     label_selection = st.selectbox("Select Node Label to Modify", options=labels, key="modify_node_label")
#     node_name_list = get_all_node_names_of_label(label_selection)
#     node_name_selection = st.selectbox("Select Node to Modify", options=node_name_list, key="modify_node_name")
#     node_attribute_list = get_node_info(label_selection, node_name_selection)
#     node_attribute_to_modify = st.selectbox("Select Attribute to Modify", options=node_attribute_list, key="modify_node_attribute")
#     new_attribute_value = st.text_input("Enter New Value for Attribute", key="modify_node_attribute_value")
#     if st.button("Modify Node"):
#         modify_node_attribute(label_selection, node_name_selection, node_attribute_to_modify, new_attribute_value)
#         st.success("Node Modified Successfully!")
# st.header("All Data Nodes")
# all_nodes = get_all_nodes()
# for node in all_nodes:
#     st.write(node)
