from uuid import UUID
from datetime import datetime, timedelta, date
from typing import Optional, Dict, List, Any, Type, Generic, TypeVar
from math import ceil
from sqlalchemy import select, asc, desc, func, or_, and_, not_
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.logger_config import configure_logging
from app.config.constants import DatabaseErrorMessages
from app.exception.baseapp_exception import InternalServerErrorException

# Configure logging
configure_logging()

# Generic type for the model
ModelType = TypeVar('ModelType')

# Frontend to Backend operator mapping
OPERATOR_MAPPING = {
    # Number operators
    "equal_to": "eq",
    "not_equal_to": "ne", 
    "greater_than": "gt",
    "less_than": "lt",
    "between": "between",
    "greater_than_or_equal": "gte",
    "less_than_or_equal": "lte",
    
    # Text operators
    "is": "is",
    "is_not": "is_not",
    "contains": "contains",
    "does_not_contain": "not_contains",
    "starts_with": "startswith",
    "ends_with": "endswith",
    "is_empty": "is_empty",
    "is_not_empty": "not_empty",
    
    # Boolean operators (same as text)
    # Enum operators (same as text)
    
    # Date operators (keep as is)
    "today": "today",
    "yesterday": "yesterday",
    "previous_day": "previous_day",
    "previous_7_days": "previous_7_days",
    "previous_30_days": "previous_30_days",
    "previous_1_month": "previous_1_month",
    "previous_3_months": "previous_3_months",
    "previous_12_months": "previous_12_months",
    "before": "before",
    "after": "after",
    "on": "on",
    "previous": "previous",
    "current": "current",
    "next": "next",
    
    # Time operators
    "this_hour": "this_hour",
    "last_hour": "last_hour",
    "last_3_hours": "last_3_hours",
    "morning": "morning",
    "afternoon": "afternoon",
    "evening": "evening",
    "night": "night"
    
}

def map_frontend_operator(operator: str) -> str:
    """Map frontend operator to backend operator"""
    return OPERATOR_MAPPING.get(operator, operator)


def parse_date_value(value: Any) -> Optional[datetime]:
    """
    Parse various date formats to datetime object.
    Handles: datetime objects, date objects, ISO strings, timestamps
    """
    if value is None:
        return None
    
    if isinstance(value, datetime):
        return value
    
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    
    if isinstance(value, str):
        try:
            # Try ISO format first
            # Be flexible with separator between date and time
            value = value.replace(':', 'T', 1) if value.count(':') > 1 else value
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            try:
                # Try common date formats
                for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d', '%d-%m-%Y']:
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        continue
            except:
                pass
    
    if isinstance(value, (int, float)):
        try:
            # Assume timestamp
            return datetime.fromtimestamp(value)
        except:
            pass
    
    return None


class BaseAppRepository(Generic[ModelType]):
    """Base repository class that can be reused by all repositories."""

    def __init__(self, db: AsyncSession, model: Type[ModelType]):
        self.db = db
        self.model = model
        # logger.info(f" {self.__class__.__name__} initialized with DB session: {id(db)}")  # Disabled to reduce log noise

    async def get_all(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        search: Optional[str] = None,
        order_by: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        user_id: Optional[UUID] = None,
        workspace_id: Optional[UUID] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get all records with dynamic filters + search + ordering + pagination.
        """
        # filters = filters or []
        query = select(self.model)
        # Get primary key column for counting
        primary_key_col = None
        for col_name in dir(self.model):
            if not col_name.startswith('_'):
                col_attr = getattr(self.model, col_name)
                if hasattr(col_attr, 'primary_key') and col_attr.primary_key:
                    primary_key_col = col_attr
                    break
        
        if primary_key_col:
            count_query = select(func.count(primary_key_col))
        else:
            count_query = select(func.count()).select_from(self.model)

        where_clauses = []
        count_clauses = []

        # --- Handle dynamic filters ---
        filter_rules = []
        overall_logic = "AND"

        if isinstance(filters, dict):
            filter_rules = filters.get("Filters", [])
            overall_logic = filters.get("logic", "AND")
        elif isinstance(filters, list): # Fallback for old format
            filter_rules = filters

        for f in filter_rules:
            col_name = f.get("column")
            operator = map_frontend_operator(f.get("operator"))  # Map frontend operator to backend
            value = f.get("value")
            logical = f.get("logical", "and")
            case_sensitive = f.get("caseSensitive", False)
            columns = f.get("columns", [col_name]) if col_name == "search" else [col_name]
            value2 = f.get("value2")

            clause = None
            for col in columns:
                # Add a guard clause to prevent processing if the column name is None
                if col is None:
                    continue

                if not hasattr(self.model, col):
                    continue
                column_attr = getattr(self.model, col)
                col_type = str(column_attr.type).lower()
                clause_part = None

                # --- Number filters ---
                if any(t in col_type for t in ["int", "numeric", "float", "decimal"]):
                    if operator == "eq":
                        clause_part = column_attr == value
                    elif operator == "ne":
                        clause_part = column_attr != value
                    elif operator == "gt":
                        clause_part = column_attr > value
                    elif operator == "gte":
                        clause_part = column_attr >= value
                    elif operator == "lt":
                        clause_part = column_attr < value
                    elif operator == "lte":
                        clause_part = column_attr <= value
                    elif operator == "between":
                        clause_part = column_attr.between(value, value2)
                    elif operator == "is_empty":
                        clause_part = column_attr.is_(None)
                    elif operator == "not_empty":
                        clause_part = column_attr.is_not(None)

                # --- Text filters ---
                elif any(t in col_type for t in ["char", "text", "string"]):
                    cmp_func = column_attr if case_sensitive else func.lower(column_attr)
                    cmp_value = value if case_sensitive else str(value).lower()

                    if operator == "is":
                        clause_part = cmp_func == cmp_value
                    elif operator == "is_not":
                        clause_part = cmp_func != cmp_value
                    elif operator == "as_it":  # Case-insensitive equality
                        clause_part = func.lower(column_attr) == cmp_value
                    elif operator == "contains":
                        clause_part = column_attr.ilike(f"%{value}%") if not case_sensitive else column_attr.like(f"%{value}%")
                    elif operator == "not_contains":
                        clause_part = ~column_attr.ilike(f"%{value}%") if not case_sensitive else ~column_attr.like(f"%{value}%")
                    elif operator == "startswith":
                        clause_part = column_attr.ilike(f"{value}%") if not case_sensitive else column_attr.like(f"{value}%")
                    elif operator == "endswith":
                        clause_part = column_attr.ilike(f"%{value}") if not case_sensitive else column_attr.like(f"%{value}")
                    elif operator == "is_empty":
                        clause_part = column_attr.is_(None)
                    elif operator == "not_empty":
                        clause_part = column_attr.is_not(None)

                # --- Boolean filters ---
                elif "bool" in col_type:
                    # Convert string 'true'/'false' to Python boolean
                    bool_value = None
                    if isinstance(value, str):
                        if value.lower() == 'true':
                            bool_value = True
                        elif value.lower() == 'false':
                            bool_value = False
                    elif isinstance(value, bool):
                        bool_value = value

                    if operator == "is":
                        clause_part = column_attr.is_(bool_value)
                    elif operator == "is_not":
                        clause_part = column_attr.isnot(bool_value)
                    elif operator == "is_empty":
                        clause_part = column_attr.is_(None)
                    elif operator == "not_empty":
                        clause_part = column_attr.is_not(None)

                # --- Enum filters ---
                elif "enum" in col_type:
                    if operator == "is":
                        clause_part = column_attr == value
                    elif operator == "is_not":
                        clause_part = column_attr != value
                    elif operator == "is_empty":
                        clause_part = column_attr.is_(None)
                    elif operator == "not_empty":
                        clause_part = column_attr.is_not(None)

                # --- Date / Time filters ---
                elif any(t in col_type for t in ["date", "time", "timestamp"]):
                    now = datetime.now()
                    today = date.today()

                    # Date operators
                    if operator == "today":
                        clause_part = func.date(column_attr) == today
                    elif operator == "yesterday":
                        clause_part = func.date(column_attr) == today - timedelta(days=1)
                    elif operator == "previous_day":
                        clause_part = func.date(column_attr) == today - timedelta(days=2)
                    elif operator == "prev_7_days" or operator == "previous_7_days":
                        clause_part = column_attr >= today - timedelta(days=7)
                    elif operator == "prev_30_days" or operator == "previous_30_days":
                        clause_part = column_attr >= today - timedelta(days=30)
                    elif operator == "previous_1_month":
                        # First day of previous month
                        first_day_prev_month = today.replace(day=1) - timedelta(days=1)
                        first_day_prev_month = first_day_prev_month.replace(day=1)
                        # Last day of previous month
                        last_day_prev_month = today.replace(day=1) - timedelta(days=1)
                        clause_part = func.date(column_attr).between(first_day_prev_month, last_day_prev_month)
                    elif operator == "previous_3_months":
                        clause_part = column_attr >= today - timedelta(days=90)
                    elif operator == "previous_12_months":
                        clause_part = column_attr >= today - timedelta(days=365)
                    elif operator == "between":
                        start_date = parse_date_value(value)
                        end_date = parse_date_value(value2)
                        
                        if start_date and end_date:
                            # Use proper date casting based on column type
                            if "timestamp" in col_type:
                                clause_part = column_attr.between(start_date, end_date)
                            else:  # date type
                                clause_part = column_attr.between(start_date.date(), end_date.date())
                    elif operator == "before":
                        parsed_value = parse_date_value(value)
                        if parsed_value:
                            clause_part = column_attr < parsed_value
                    elif operator == "after":
                        parsed_value = parse_date_value(value)
                        if parsed_value:
                            clause_part = column_attr > parsed_value
                    elif operator == "on":
                        parsed_value = parse_date_value(value)
                        if parsed_value:
                            clause_part = func.date(column_attr) == parsed_value.date()
                    
                    # Time operators
                    elif operator == "this_hour":
                        clause_part = func.date_trunc('hour', column_attr) == now.replace(minute=0, second=0, microsecond=0)
                    elif operator == "last_hour":
                        last_hour = now - timedelta(hours=1)
                        clause_part = column_attr.between(last_hour, now)
                    elif operator == "last_3_hours":
                        last_3_hours = now - timedelta(hours=3)
                        clause_part = column_attr.between(last_3_hours, now)
                    elif operator == "morning":
                        # 6 AM to 12 PM
                        morning_start = now.replace(hour=6, minute=0, second=0, microsecond=0)
                        morning_end = now.replace(hour=12, minute=0, second=0, microsecond=0)
                        clause_part = func.time(column_attr).between(morning_start.time(), morning_end.time())
                    elif operator == "afternoon":
                        # 12 PM to 5 PM
                        afternoon_start = now.replace(hour=12, minute=0, second=0, microsecond=0)
                        afternoon_end = now.replace(hour=17, minute=0, second=0, microsecond=0)
                        clause_part = func.time(column_attr).between(afternoon_start.time(), afternoon_end.time())
                    elif operator == "evening":
                        # 5 PM to 10 PM
                        evening_start = now.replace(hour=17, minute=0, second=0, microsecond=0)
                        evening_end = now.replace(hour=22, minute=0, second=0, microsecond=0)
                        clause_part = func.time(column_attr).between(evening_start.time(), evening_end.time())
                    elif operator == "night":
                        # 10 PM to 6 AM (next day)
                        night_start = now.replace(hour=22, minute=0, second=0, microsecond=0)
                        night_end = now.replace(hour=6, minute=0, second=0, microsecond=0)
                        clause_part = or_(
                            func.time(column_attr) >= night_start.time(),
                            func.time(column_attr) <= night_end.time()
                        )
                    
                    # Relative range operators (enhanced)
                    elif operator == "previous":
                        # Handle relative date range from value, check both casings
                        rel_range = f.get("relative_date_range") or f.get("relativeDateRange")
                        if rel_range:
                            period_type = rel_range.get("period_type") or rel_range.get("periodType", "day")
                            count = rel_range.get("count", 1)
                            include_today = rel_range.get("include_today") or rel_range.get("includeToday", False)

                            days_to_subtract = 0
                            if period_type == "day":
                                days_to_subtract = count
                            elif period_type == "week":
                                days_to_subtract = count * 7
                            elif period_type == "month":
                                days_to_subtract = count * 30  # Approximation
                            elif period_type == "year":
                                days_to_subtract = count * 365 # Approximation

                            if days_to_subtract > 0:
                                if include_today:
                                    # Range: [today - (days-1), today]
                                    # Example: previous 7 days including today is from 6 days ago until the end of today.
                                    start_date = today - timedelta(days=days_to_subtract - 1)
                                    end_date = today + timedelta(days=1) # End of today
                                    clause_part = and_(
                                        column_attr >= datetime.combine(start_date, datetime.min.time()),
                                        column_attr < datetime.combine(end_date, datetime.min.time())
                                    )
                                else:
                                    # Range: [today - days, yesterday]
                                    # Example: previous 7 days excluding today is from 7 days ago until the end of yesterday.
                                    start_date = today - timedelta(days=days_to_subtract)
                                    end_date = today # End of yesterday
                                    clause_part = and_(
                                        column_attr >= datetime.combine(start_date, datetime.min.time()),
                                        column_attr < datetime.combine(end_date, datetime.min.time())
                                    )

                    elif operator == "current":
                        # Handle current period
                        rel_range = f.get("relative_date_range") or f.get("relativeDateRange")
                        if rel_range:
                            period_type = rel_range.get("period_type") or rel_range.get("periodType", "day")
                            
                            if period_type == "day":
                                clause_part = func.date(column_attr) == today
                            elif period_type == "week":
                                # Current week (Monday to Sunday)
                                start_of_week = today - timedelta(days=today.weekday())
                                end_of_week = start_of_week + timedelta(days=6)
                                clause_part = func.date(column_attr).between(start_of_week, end_of_week)
                            elif period_type == "month":
                                # Current month
                                start_of_month = today.replace(day=1)
                                if today.month == 12:
                                    end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
                                else:
                                    end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
                                clause_part = func.date(column_attr).between(start_of_month, end_of_month)
                    elif operator == "next":
                        # Handle next period
                        rel_range = f.get("relative_date_range") or f.get("relativeDateRange")
                        if rel_range:
                            period_type = rel_range.get("period_type") or rel_range.get("periodType", "day")
                            count = rel_range.get("count", 1)
                            include_today = rel_range.get("include_today") or rel_range.get("includeToday", False)
                            
                            if period_type == "day":
                                if include_today:
                                    # Include today: from today to (today + count - 1)
                                    clause_part = and_(
                                        column_attr >= datetime.combine(today, datetime.min.time()),
                                        column_attr < datetime.combine(today + timedelta(days=count), datetime.min.time())
                                    )
                                else:
                                    # Exclude today: from tomorrow to (today + count)
                                    clause_part = and_(
                                        column_attr >= datetime.combine(today + timedelta(days=1), datetime.min.time()),
                                        column_attr < datetime.combine(today + timedelta(days=count + 1), datetime.min.time())
                                    )
                            elif period_type == "week":
                                weeks_in_days = count * 7
                                if include_today:
                                    clause_part = and_(
                                        column_attr >= datetime.combine(today, datetime.min.time()),
                                        column_attr < datetime.combine(today + timedelta(days=weeks_in_days), datetime.min.time())
                                    )
                                else:
                                    clause_part = and_(
                                        column_attr >= datetime.combine(today + timedelta(days=1), datetime.min.time()),
                                        column_attr < datetime.combine(today + timedelta(days=weeks_in_days + 1), datetime.min.time())
                                    )
                            elif period_type == "month":
                                months_in_days = count * 30
                                if include_today:
                                    clause_part = and_(
                                        column_attr >= datetime.combine(today, datetime.min.time()),
                                        column_attr < datetime.combine(today + timedelta(days=months_in_days), datetime.min.time())
                                    )
                                else:
                                    clause_part = and_(
                                        column_attr >= datetime.combine(today + timedelta(days=1), datetime.min.time()),
                                        column_attr < datetime.combine(today + timedelta(days=months_in_days + 1), datetime.min.time())
                                    )

                if clause_part is not None:
                    if clause is None:
                        clause = clause_part
                    else:
                        # Use logical operator to combine clauses
                        if logical == "or":
                            clause = or_(clause, clause_part)
                        else:  # default to "and"
                            clause = and_(clause, clause_part)

            if clause is not None:
                if logical == "not":
                    where_clauses.append(not_(clause))
                    count_clauses.append(not_(clause))
                else:  # "and" and "or" cases are identical
                    where_clauses.append(clause)
                    count_clauses.append(clause)

        # --- Handle search ---
        search_clauses = []
        if search:
            # Find all string columns that can be searched
            for column_name in dir(self.model):
                if not column_name.startswith('_'):
                    column_attr = getattr(self.model, column_name)
                    if hasattr(column_attr, 'type'):
                        col_type = str(column_attr.type).lower()
                        if any(t in col_type for t in ["char", "text", "string"]):
                            search_clauses.append(column_attr.ilike(f"%{search}%"))
            
            if search_clauses:
                search_condition = or_(*search_clauses)
                # This will be added to the final clauses later

        # --- Apply WHERE clauses ---
        final_clauses = []
        
        # 1. Group user-defined filters from `where_clauses`
        if where_clauses:
            if overall_logic.upper() == "ANY" or overall_logic.upper() == "OR":
                final_clauses.append(or_(*where_clauses))
            else: # Default to AND
                final_clauses.append(and_(*where_clauses))

        # 2. Add search clause (if it exists)
        if search_clauses:
            final_clauses.append(or_(*search_clauses))
        # 3. Add default status filter to exclude deleted items
        if hasattr(self.model, 'status'):
            final_clauses.append(getattr(self.model, 'status') != "deleted")

        if final_clauses:
            query = query.where(and_(*final_clauses))
            count_query = count_query.where(and_(*final_clauses))

        # --- Handle ordering ---
        if order_by:
            desc_order = order_by.startswith("-")
            field_name = order_by[1:] if desc_order else order_by
            if hasattr(self.model, field_name):
                column_attr = getattr(self.model, field_name)
                query = query.order_by(desc(column_attr) if desc_order else asc(column_attr))
        else:
            if hasattr(self.model, 'created_at'):
                query = query.order_by(desc(getattr(self.model, 'created_at')))

        # --- Pagination ---
        query = query.offset(skip).limit(limit)

        # --- Execute queries ---
        try:
            total_count = (await self.db.execute(count_query)).scalar() or 0
            result = await self.db.execute(query)
            data = result.scalars().all()

            pagination = {
                "total_count": total_count,
                "offset": skip,
                "limit": limit,
                "total_pages": ceil(total_count / limit) if limit else 1,
            }

            return {"data": data, "pagination": pagination}
        except Exception as e:
            raise InternalServerErrorException(message=f"{DatabaseErrorMessages.DATA_RETRIEVAL_ERROR}: {str(e)}") from e