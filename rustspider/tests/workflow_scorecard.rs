use rustspider::connector::InMemoryConnector;
use rustspider::event_bus::InMemoryEventBus;
use rustspider::workflow::{FlowJob, FlowStep, MemoryWorkflowContext, WorkflowRunner};
use serde_json::{Map, Value};

#[test]
fn workflow_runner_executes_steps_and_emits_outputs() {
    let event_bus = InMemoryEventBus::new(32);
    let connector = InMemoryConnector::default();
    let runner = WorkflowRunner::new()
        .with_event_bus(event_bus)
        .add_connector(connector);

    let mut context = MemoryWorkflowContext::default();
    context.set_title("Rust Workflow");
    let job = FlowJob {
        id: "rust-workflow".to_string(),
        name: "rust-workflow".to_string(),
        steps: vec![
            FlowStep {
                id: "goto".to_string(),
                step_type: "goto".to_string(),
                selector: "https://example.com".to_string(),
                value: String::new(),
                metadata: Map::new(),
            },
            FlowStep {
                id: "title".to_string(),
                step_type: "extract".to_string(),
                selector: "title".to_string(),
                value: String::new(),
                metadata: Map::new(),
            },
        ],
        output_contract: Map::new(),
        policy: Default::default(),
    };

    let result = runner
        .execute_with_context(&job, &mut context)
        .expect("workflow should succeed");
    assert_eq!(result.job_id, "rust-workflow");
    assert_eq!(
        result.extracted["title"],
        Value::String("Rust Workflow".to_string())
    );
}
