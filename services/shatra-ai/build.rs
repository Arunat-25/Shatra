fn main() -> Result<(), Box<dyn std::error::Error>> {
    let proto = "../../proto/shatra/ai/v1/ai.proto";
    tonic_build::configure()
        .build_server(true)
        .compile_protos(&[proto], &["../../proto"])?;
    Ok(())
}
