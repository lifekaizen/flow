from functools import reduce
from sqlalchemy import or_
from sqlalchemy.sql import func
from sqlalchemy.orm import aliased

from flask import request
from flask_restx import Resource, fields, Namespace

from authorization import AuthError, requires_auth, requires_scope, check_access
from database import versioned_row_to_dict, Protocol, ProtocolVersion, Run, RunVersion, run_to_sample, Sample, SampleVersion

from api.protocol import protocol_output
from api.run import run_output
from api.utils import filter_by_plate_label, filter_by_reagent_label, filter_by_sample_label, protocol_id_param, run_id_param, version_id_param, purge_param, user_id_param, method_param, sample_id_param, protocol_param, plate_param, sample_param, reagent_param, creator_param, archived_param, page_param, per_page_param


api = Namespace('search-results', description='Operations for searching for runs and protocols with various filters.', path='/')


search_results = api.model('SearchResults', {
    'protocols': fields.List(fields.Nested(protocol_output)),
    'runs': fields.List(fields.Nested(run_output))
})


def all_protocols(include_archived=False):
    query = Protocol.query
    if not include_archived:
        query = query.filter(Protocol.is_deleted != True)
    return query

def all_runs(include_archived=False):
    query = Run.query
    if not include_archived:
        query = query.filter(Run.is_deleted != True)
    return query

def all_samples(include_archived=False):
    query = Sample.query
    if not include_archived:
        query = query.filter(Sample.is_deleted != True)
    return query


@api.route('/search')
class ProtocolsResource(Resource):
    @api.doc(
        security='token',
        model=search_results,
        params={
            'protocol': protocol_param,
            'run': run_param,
            'plate': plate_param,
            'sample': sample_param,
            'reagent': reagent_param,
            'creator': creator_param,
            'archived': archived_param,
            'page': page_param,
            'per_page': per_page_param,
        }
    )
    @requires_auth
    @requires_scope('read:protocols')
    @requires_scope('read:runs')
    def get(self):
        protocol = int(request.args.get('protocol')) if request.args.get('protocol') else None
        run = int(request.args.get('run')) if request.args.get('run') else None
        plate = request.args.get('plate')
        reagent = request.args.get('reagent')
        sample = request.args.get('sample')
        creator = request.args.get('creator')
        archived = request.args.get('archived') == 'true' if request.args.get('archived') else False

        protocols_queries = []
        runs_queries = []
        samples_queries = []

        # Add filter specific queries. These will be intersected later on.
        if protocol:
            protocols_queries.append(
                all_protocols().filter(Protocol.id == protocol)
            )
            runs_queries.append(
                all_runs(archived)\
                    .join(ProtocolVersion, ProtocolVersion.id == Run.protocol_version_id)\
                    .filter(ProtocolVersion.protocol_id == protocol)
            )
            samples_queries.append(
                all_samples(archived)\
                    .join(ProtocolVersion, ProtocolVersion.id == Sample.protocol_version_id)\
                    .filter(ProtocolVersion.protocol_id == protocol)
            )
        if run:
            protocols_queries.append(
                all_protocols(archived)\
                    .join(ProtocolVersion, ProtocolVersion.protocol_id == Protocol.id)\
                    .join(Run, Run.protocol_version_id == ProtocolVersion.id)\
                    .filter(Run.id == run)
            )
            runs_queries.append(
                all_runs(archived).filter(Run.id == run)
            )
            samples_queries.append(
                all_samples(archived)\
                    .join(RunVersion, RunVersion.id == Sample.run_version_id)\
                    .filter(RunVersion.run_id == run)
            )
        if plate:
            run_version_query = all_runs(archived)\
                .join(RunVersion, RunVersion.id == Run.version_id)
            runs_subquery = filter_by_plate_label(run_version_query, plate)
            runs_queries.append(runs_subquery)

            run_version_query = all_protocols(archived)\
                .join(ProtocolVersion, ProtocolVersion.protocol_id == Protocol.id)\
                .join(Run, Run.protocol_version_id == ProtocolVersion.id)\
                .join(RunVersion, RunVersion.id == Run.version_id)
            protocols_subquery = filter_by_plate_label(run_version_query, plate)
            protocols_queries.append(protocols_subquery)

            samples_queries.append(
                all_samples(archived)\
                    .filter(Sample.plate_id == plate)
            )
        if reagent:
            run_version_query = all_runs(archived)\
                .join(RunVersion, RunVersion.id == Run.version_id)
            runs_subquery = filter_by_reagent_label(run_version_query, reagent)
            runs_queries.append(runs_subquery)

            run_version_query = all_protocols(archived)\
                .join(ProtocolVersion, ProtocolVersion.protocol_id == Protocol.id)\
                .join(Run, Run.protocol_version_id == ProtocolVersion.id)\
                .join(RunVersion, RunVersion.id == Run.version_id)
            protocols_subquery = filter_by_reagent_label(run_version_query, reagent)
            protocols_queries.append(protocols_subquery)

            run_version_query = all_samples(archived)\
                .join(RunVersion, RunVersion.id == Sample.run_version_id)
            samples_subquery = filter_by_reagent_label(run_version_query, reagent)
            samples_queries.append(samples_subquery)
        if sample:
            run_version_query = all_runs(archived)\
                .join(RunVersion, RunVersion.id == Run.version_id)
            runs_subquery = filter_by_sample_label(run_version_query, sample)
            runs_queries.append(runs_subquery)

            run_version_query = all_protocols(archived)\
                .join(ProtocolVersion, ProtocolVersion.protocol_id == Protocol.id)\
                .join(Run, Run.protocol_version_id == ProtocolVersion.id)\
                .join(RunVersion, RunVersion.id == Run.version_id)
            protocols_subquery = filter_by_sample_label(run_version_query, sample)
            protocols_queries.append(protocols_subquery)

            samples_queries.append(
                all_samples(archived)\
                    .filter(Sample.sample_id == sample)
            )
        if creator:
            protocols_queries.append(
                all_protocols(archived)\
                    # .filter(Protocol.id == protocol)\
                    .filter(Protocol.created_by == creator)
            )
            runs_queries.append(
                all_runs(archived)\
                    # .filter(Run.id == run)
                    .filter(Run.created_by == creator)
            )
            samples_queries.append(
                all_samples(archived)\
                    .filter(Sample.created_by == creator)
            )

        # Add a basic non-deleted items query if no filters were specified.
        if len(protocols_queries) == 0:
            protocols_queries.append(all_protocols(archived))
        if len(runs_queries) == 0:
            runs_queries.append(all_runs(archived))
        if len(samples_queries) == 0:
            samples_queries.append(all_samples(archived))

        # Only return the intersection of all queries.
        protocols_query = reduce(lambda a, b: a.intersect(b), protocols_queries)
        runs_query = reduce(lambda a, b: a.intersect(b), runs_queries)
        samples_query = reduce(lambda a, b: a.intersect(b), samples_queries)

        # Handle pagination.
        if request.args.get('page') is not None or request.args.get('per_page') is not None:
            page = int(request.args.get('page')) if request.args.get('page') else 1
            per_page = int(request.args.get('per_page')) if request.args.get('per_page') else 20

            protocol_results = protocols_query.distinct().paginate(page=page, per_page=per_page).items
            run_results = runs_query.distinct().paginate(page=page, per_page=per_page).items
            sample_results = samples_query.distinct().paginate(page=page, per_page=per_page).items
        else:
            protocol_results = protocols_query.distinct()
            run_results = runs_query.distinct()
            sample_results = samples_query.distinct()

        # Convert database models to dictionaries and return the serch results.
        protocols = [
            versioned_row_to_dict(api, protocol, protocol.current)
            for protocol
            in protocol_results
            if check_access(path=f"/protocol/{str(protocol.id)}", method="GET")
        ]
        runs = [
            versioned_row_to_dict(api, run, run.current)
            for run
            in run_results
            if check_access(path=f"/run/{str(run.id)}", method="GET")
        ]
        samples = [
            run_to_sample(sample)
            for sample
            in sample_results
            if check_access(path=f"/run/{str(sample.run_version.run_id)}", method="GET")
        ]
        return {
            'protocols': protocols,
            'runs': runs,
            'samples': samples,
        }
