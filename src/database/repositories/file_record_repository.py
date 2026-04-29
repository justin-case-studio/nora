"""
Repository for file records in the Notarizer application.
Handles database operations related to registered files.
"""
from ..db_manager import DatabaseManager
from ..models import FileRecord
from pathlib import Path


class FileRecordRepository:
    """Repository for file records."""

    def __init__(self):
        """Initialize the repository with a database manager."""
        self.db_manager = DatabaseManager()

    def create(self, file_record):
        """Create a new file record in the database."""
        query = '''
        INSERT INTO file_records
        (file_path, file_name, size, modified_date, sha256, tx_id, registered_at, is_onchain, user_notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        params = (
            file_record.file_path,
            file_record.file_name,
            file_record.size,
            file_record.modified_date,
            file_record.sha256,
            file_record.tx_id,
            file_record.registered_at,
            int(file_record.is_onchain), # Convert boolean to int for SQLite
            file_record.user_notes
        )

        success = self.db_manager.execute_write(query, params)
        if not success:
            print(f"❌ [FileRecordRepo] Failed to create record for: {file_record.file_name}")
        return file_record if success else None

    def find_by_id(self, record_id):
        """Find a file record by its ID."""
        query = 'SELECT * FROM file_records WHERE id = ?'
        row = self.db_manager.execute_read(query, (record_id,), fetch_one=True)

        return FileRecord.from_row(row)

    def find_by_hash(self, sha256, blockchain_target: str):
        """Find file records by their SHA-256 hash, filtered by blockchain_target (using is_onchain column)."""
        base_query = 'SELECT * FROM file_records WHERE sha256 = ?'
        params = [sha256]

        if blockchain_target == 'local':
            base_query += ' AND is_onchain = ?'
            params.append(0) # False for local
        elif blockchain_target == 'MintBlue':
            base_query += ' AND is_onchain = ?'
            params.append(1) # True for onchain
        # If blockchain_target is something else or not specified, no additional filtering on is_onchain occurs for find_by_hash by default.
        # This might be desired if one wants to find a hash regardless of its onchain status if target is not local/MintBlue.
        # However, current API logic always passes 'local' or 'MintBlue', so this branch is effectively covered.

        base_query += ' ORDER BY registered_at ASC'

        rows = self.db_manager.execute_read(base_query, tuple(params))
        return [FileRecord.from_row(row) for row in rows] if rows else []

    def find_by_file_metadata(self, file_path, file_name, size, modified_date):
        """Find a file record by its metadata."""
        query = '''
        SELECT * FROM file_records
        WHERE file_path = ? AND file_name = ? AND size = ? AND modified_date = ?
        '''
        params = (file_path, file_name, size, modified_date)
        row = self.db_manager.execute_read(query, params, fetch_one=True)

        return FileRecord.from_row(row)

    def exists(self, file_path, file_name, size, modified_date, blockchain_target: str):
        """Check if a file record exists with the given metadata, filtered by blockchain_target."""
        base_query = '''
        SELECT 1 FROM file_records
        WHERE file_path = ? AND file_name = ? AND size = ? AND modified_date = ?
        '''
        params = [file_path, file_name, size, modified_date]

        # Add filtering based on blockchain_target
        if blockchain_target == 'local':
            base_query += ' AND is_onchain = ?'
            params.append(0)  # False for local
        elif blockchain_target == 'MintBlue':  # Assuming 'MintBlue' is the other target
            base_query += ' AND is_onchain = ?'
            params.append(1)  # True for onchain
        # If blockchain_target is something else, this query will not filter by is_onchain,
        # effectively checking existence across both modes if not 'local' or 'MintBlue'.
        # This behavior should be confirmed based on requirements, but typically a target is always given.

        base_query += ' LIMIT 1'

        row = self.db_manager.execute_read(base_query, tuple(params), fetch_one=True)
        return row is not None

    def get_all(self, blockchain_target: str, limit=100, offset=0):
        """Get all file records with pagination, filtered by blockchain_target (using is_onchain column)."""
        base_query = 'SELECT * FROM file_records'
        params = []
        where_clauses = []

        if blockchain_target == 'local':
            where_clauses.append('is_onchain = ?')
            params.append(0)
        elif blockchain_target == 'MintBlue':
            where_clauses.append('is_onchain = ?')
            params.append(1)

        if where_clauses:
            base_query += ' WHERE ' + ' AND '.join(where_clauses)

        base_query += ' ORDER BY registered_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        rows = self.db_manager.execute_read(base_query, tuple(params))
        return [FileRecord.from_row(row) for row in rows] if rows else []

    def get_latest_registration_date(self, blockchain_target: str):
        """Get the timestamp of the most recent registration for the given blockchain_target."""
        base_query = 'SELECT registered_at FROM file_records'
        params = []
        where_clauses = []

        if blockchain_target == 'local':
            where_clauses.append('is_onchain = ?')
            params.append(0)
        elif blockchain_target == 'MintBlue':
            where_clauses.append('is_onchain = ?')
            params.append(1)
        # If no specific target, or an unknown one, it will fetch the absolute latest from all records.
        # However, the API will always call this with a known target for dashboard stats.

        if where_clauses:
            base_query += ' WHERE ' + ' AND '.join(where_clauses)

        base_query += ' ORDER BY registered_at DESC LIMIT 1'

        row = self.db_manager.execute_read(base_query, tuple(params), fetch_one=True)
        return row['registered_at'] if row else None

    def count(self, blockchain_target: str):
        """Count the total number of file records, filtered by blockchain_target (using is_onchain column)."""
        base_query = 'SELECT COUNT(*) as count FROM file_records'
        params = []
        where_clauses = []

        if blockchain_target == 'local':
            where_clauses.append('is_onchain = ?')
            params.append(0)
        elif blockchain_target == 'MintBlue':
            where_clauses.append('is_onchain = ?')
            params.append(1)

        if where_clauses:
            base_query += ' WHERE ' + ' AND '.join(where_clauses)

        row = self.db_manager.execute_read(base_query, tuple(params), fetch_one=True)
        return row['count'] if row else 0

    def _build_search_where_clause(self, search_term=None, blockchain_target=None, start_date=None, end_date=None):
        """Helper method to build the WHERE clause and parameters for search queries."""
        params = []
        text_search_clauses = []
        filter_clauses = []

        # Always filter by blockchain mode first
        if blockchain_target == 'local':
            filter_clauses.append('is_onchain = ?')
            params.append(0)
        elif blockchain_target == 'MintBlue':
            filter_clauses.append('is_onchain = ?')
            params.append(1)

        # Text search condition for multiple fields
        if search_term:
            like_term = f'%{search_term}%'
            text_search_clauses.append('file_name LIKE ?')
            text_search_clauses.append('file_path LIKE ?')
            text_search_clauses.append('sha256 LIKE ?')
            text_search_clauses.append('tx_id LIKE ?')
            text_search_clauses.append('user_notes LIKE ?')
            # Add the parameter 5 times, once for each field
            params.extend([like_term] * 5)

        # Combine text search clauses with OR
        if text_search_clauses:
            filter_clauses.append(f"({' OR '.join(text_search_clauses)})")

        # Date range conditions
        if start_date:
            filter_clauses.append("registered_at >= ?")
            params.append(start_date)
        if end_date:
            # To be inclusive of the end date, we search for records strictly
            # less than the day *after* the end date. This is the most robust
            # way to handle timestamps.
            filter_clauses.append("registered_at < date(?, '+1 day')")
            params.append(end_date)

        where_sql = ' WHERE ' + ' AND '.join(filter_clauses) if filter_clauses else ''

        return where_sql, tuple(params)

    def count_search_results(self, search_term=None, blockchain_target=None, start_date=None, end_date=None):
        """Count the total number of records matching the search criteria."""
        base_query = 'SELECT COUNT(*) as count FROM file_records'
        where_sql, params = self._build_search_where_clause(search_term, blockchain_target, start_date, end_date)

        full_query = base_query + where_sql
        row = self.db_manager.execute_read(full_query, params, fetch_one=True)
        return row['count'] if row else 0

    def search(self, search_term, blockchain_target: str, limit=100, offset=0, start_date=None, end_date=None):
        """
        Search for file records by various criteria with optional date range filtering.
        """
        base_query = 'SELECT * FROM file_records'
        where_sql, params = self._build_search_where_clause(search_term, blockchain_target, start_date, end_date)

        query = base_query + where_sql
        query += ' ORDER BY registered_at DESC LIMIT ? OFFSET ?'

        paged_params = params + (limit, offset)

        rows = self.db_manager.execute_read(query, paged_params)
        return [FileRecord.from_row(row) for row in rows] if rows else []

    def find_by_path(self, file_path):
        """
        Find file records by their file path.

        This method handles both full paths and parent directory + filename combinations.

        Args:
            file_path: The full path to the file

        Returns:
            List of FileRecord objects matching the path
        """
        # Convert to Path object to extract parent and name
        path_obj = Path(file_path)
        parent_dir = str(path_obj.parent)
        file_name = path_obj.name

        # Query for records matching either the full path or parent + name combination
        query = '''
        SELECT * FROM file_records
        WHERE file_path = ? OR (file_path = ? AND file_name = ?)
        ORDER BY registered_at ASC
        '''
        rows = self.db_manager.execute_read(query, (file_path, parent_dir, file_name))

        return [FileRecord.from_row(row) for row in rows]

    def update_user_notes(self, record_id, user_notes):
        """Update the user notes for a file record by its ID."""
        query = 'UPDATE file_records SET user_notes = ? WHERE id = ?'
        params = (user_notes, record_id)

        success = self.db_manager.execute_write(query, params)
        if not success:
            print(f"❌ [FileRecordRepo] Failed to update user notes for record ID: {record_id}")
        return success

    def get_registration_activity_by_day(self, blockchain_target: str, days: int = 30):
        """
        Get the number of registrations per day for the last X days.

        Args:
            blockchain_target: The target blockchain ('local' or 'MintBlue').
            days: The number of days to look back.

        Returns:
            A list of dictionaries, each with 'date' and 'count'.
        """
        from datetime import datetime, timedelta

        # Calculate the start date
        start_date = datetime.now() - timedelta(days=days)
        start_date_str = start_date.isoformat()

        # Base query
        query = """
        SELECT DATE(registered_at) as activity_date, COUNT(*) as count
        FROM file_records
        """
        params = []
        where_clauses = ["registered_at >= ?"]
        params.append(start_date_str)

        # Filter by blockchain target
        if blockchain_target == 'local':
            where_clauses.append('is_onchain = ?')
            params.append(0)
        elif blockchain_target == 'MintBlue':
            where_clauses.append('is_onchain = ?')
            params.append(1)

        if where_clauses:
            query += ' WHERE ' + ' AND '.join(where_clauses)

        query += ' GROUP BY activity_date ORDER BY activity_date ASC'

        rows = self.db_manager.execute_read(query, tuple(params))

        # To ensure we have data for every day in the range, we can create a date range
        # and fill in the counts from the query results.

        date_range = [datetime.now().date() - timedelta(days=i) for i in range(days)]
        date_range.reverse() # a list of date objects, from 30 days ago to today

        # Create a dictionary from query results for easy lookup
        results_map = {row['activity_date']: row['count'] for row in rows}

        # Format the final list for the chart
        chart_data = []
        for d in date_range:
            date_str = d.strftime('%Y-%m-%d')
            chart_data.append({
                'date': date_str,
                'count': results_map.get(date_str, 0)
            })

        return chart_data
