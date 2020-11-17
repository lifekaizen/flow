import moment from "moment";
import React from "react";
import { Table } from "react-bootstrap";
import { Link } from "react-router-dom";
import { SampleResult } from "../models/sample-result";

export interface ResultsProps {
    results: SampleResult[];
}

export function ResultsTable({ results }: ResultsProps) {
    return (
        <Table striped bordered hover>
            <thead>
                <tr>
                    <th>Sample ID</th>
                    <th>Sequencing Result</th>
                    <th>Run</th>
                    <th>Protocol</th>
                    <th>Signer</th>
                    <th>Witness</th>
                    <th>Date Completed</th>
                </tr>
            </thead>
            <tbody>
                {results.map(result => (
                    <tr key={`${result.protocolID}-${result.runID}-${result.sampleID}`}>
                        <td>{result.sampleID || <i>Unknown</i>}</td>
                        <td>{result.result || <i>Unknown</i>}</td>
                        <td>
                            {result.runID && <Link to={`/run/${result.runID}`}>{result.runID}</Link>}
                        </td>
                        <td>
                            {result.protocolID && <Link to={`/protocol/${result.protocolID}`}>{result.protocolID}</Link>}
                        </td>
                        <td>{result.signer}</td>
                        <td>{result.witness}</td>
                        <td>{result.completedOn && moment(result.completedOn).format("LLLL")}</td>
                    </tr>
                ))}
            </tbody>
        </Table>
    );
}