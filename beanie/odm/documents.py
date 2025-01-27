from typing import Optional, List, Type, Union, Tuple, Mapping

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pydantic import Field, ValidationError
from pydantic.main import BaseModel
from pymongo.client_session import ClientSession
from pymongo.results import DeleteResult, UpdateResult, InsertOneResult

from beanie.exceptions import (
    DocumentWasNotSaved,
    DocumentAlreadyCreated,
    CollectionWasNotInitialized,
    ReplaceError,
)
from beanie.odm.enums import SortDirection
from beanie.odm.fields import PydanticObjectId, ExpressionField
from beanie.odm.interfaces.update import (
    UpdateMethods,
)
from beanie.odm.models import (
    InspectionResult,
    InspectionStatuses,
    InspectionError,
)
from beanie.odm.operators.find.comparsion import In
from beanie.odm.queries.aggregation import AggregationQuery
from beanie.odm.queries.find import FindOne, FindMany
from beanie.odm.utils.collection import collection_factory


class Document(BaseModel, UpdateMethods):
    """
    Document Mapping class.

    Fields:

    - `id` - MongoDB document ObjectID "_id" field.
    Mapped to the PydanticObjectId class

    Inherited from:

    - Pydantic BaseModel
    - [UpdateMethods](/api/interfaces/#aggregatemethods)
    """

    id: Optional[PydanticObjectId] = Field(None, alias="_id")

    def __init__(self, *args, **kwargs):
        super(Document, self).__init__(*args, **kwargs)
        self.get_motor_collection()

    async def _sync(self) -> None:
        """
        Update local document from the database
        :return: None
        """
        new_instance = await self.get(self.id)
        for key, value in dict(new_instance).items():
            setattr(self, key, value)

    async def insert(
        self, session: Optional[ClientSession] = None
    ) -> "Document":
        """
        Insert the document (self) to the collection
        :return: Document
        """
        if self.id is not None:
            raise DocumentAlreadyCreated
        result = await self.get_motor_collection().insert_one(
            self.dict(by_alias=True, exclude={"id"}), session=session
        )
        self.id = PydanticObjectId(result.inserted_id)
        return self

    async def create(
        self, session: Optional[ClientSession] = None
    ) -> "Document":
        """
        The same as self.insert()
        :return: Document
        """
        return await self.insert(session=session)

    @classmethod
    async def insert_one(
        cls, document: "Document", session: Optional[ClientSession] = None
    ) -> InsertOneResult:
        """
        Insert one document to the collection
        :param document: Document - document to insert
        :param session: ClientSession - pymongo session
        :return: Document
        """
        return await cls.get_motor_collection().insert_one(
            document.dict(by_alias=True, exclude={"id"}), session=session
        )

    @classmethod
    async def insert_many(
        cls,
        documents: List["Document"],
        keep_ids: bool = False,
        session: Optional[ClientSession] = None,
    ):

        """
        Insert many documents to the collection

        :param documents:  List["Document"] - documents to insert
        :param keep_ids: bool - should it insert documents with ids
        or ignore it? Default False - ignore
        :param session: ClientSession - pymongo session
        :return: Document
        """
        if keep_ids:
            documents_list = [
                document.dict(by_alias=True) for document in documents
            ]
        else:
            documents_list = [
                document.dict(by_alias=True, exclude={"id"})
                for document in documents
            ]
        return await cls.get_motor_collection().insert_many(
            documents_list,
            session=session,
        )

    @classmethod
    async def get(
        cls,
        document_id: PydanticObjectId,
        session: Optional[ClientSession] = None,
    ) -> Union["Document", None]:
        """
        Get document by id

        :param document_id: PydanticObjectId - document id
        :param session: Optional[ClientSession] - pymongo session
        :return: Union["Document", None]
        """
        return await cls.find_one({"_id": document_id}, session=session)

    @classmethod
    def find_one(
        cls,
        *args: Union[dict, Mapping],
        projection_model: Optional[Type[BaseModel]] = None,
        session: Optional[ClientSession] = None,
    ) -> FindOne:
        """
        Find one document by criteria.
        Returns [FindOne](/api/queries/#findone) query object

        :param args: *Union[dict, Mapping] - search criteria
        :param projection_model: Optional[Type[BaseModel]] - projection model
        :param session: Optional[ClientSession] - pymongo session instance
        :return: [FindOne](/api/queries/#findone) - find query instance
        """
        return FindOne(document_model=cls).find_one(
            *args,
            projection_model=projection_model,
            session=session,
        )

    @classmethod
    def find_many(
        cls,
        *args,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        sort: Union[None, str, List[Tuple[str, SortDirection]]] = None,
        projection_model: Optional[Type[BaseModel]] = None,
        session: Optional[ClientSession] = None,
    ) -> FindMany:
        """
        Find many documents by criteria.
        Returns [FindMany](/api/queries/#findmany) query object

        :param args: *Union[dict, Mapping] - search criteria
        :param skip: Optional[int] - The number of documents to omit.
        :param limit: Optional[int] - The maximum number of results to return.
        :param sort: Union[None, str, List[Tuple[str, SortDirection]]] - A key
        or a list of (key, direction) pairs specifying the sort order
        for this query.
        :param projection_model: Optional[Type[BaseModel]] - projection model
        :param session: Optional[ClientSession] - pymongo session
        :return: [FindMany](/api/queries/#findmany) - query instance
        """
        return FindMany(document_model=cls).find_many(
            *args,
            sort=sort,
            skip=skip,
            limit=limit,
            projection_model=projection_model,
            session=session,
        )

    @classmethod
    def find(
        cls,
        *args,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        sort: Union[None, str, List[Tuple[str, SortDirection]]] = None,
        projection_model: Optional[Type[BaseModel]] = None,
        session: Optional[ClientSession] = None,
    ) -> FindMany:
        """
        The same as find_many
        """
        return cls.find_many(
            *args,
            skip=skip,
            limit=limit,
            sort=sort,
            projection_model=projection_model,
            session=session,
        )

    @classmethod
    def find_all(
        cls,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        sort: Union[None, str, List[Tuple[str, SortDirection]]] = None,
        projection_model: Optional[Type[BaseModel]] = None,
        session: Optional[ClientSession] = None,
    ) -> FindMany:
        """
        Get all the documents

        :param skip: Optional[int] - The number of documents to omit.
        :param limit: Optional[int] - The maximum number of results to return.
        :param sort: Union[None, str, List[Tuple[str, SortDirection]]] - A key
        or a list of (key, direction) pairs specifying the sort order
        for this query.
        :param projection_model: Optional[Type[BaseModel]] - projection model
        :param session: Optional[ClientSession] - pymongo session
        :return: [FindMany](/api/queries/#findmany) - query instance
        """
        return cls.find_many(
            {},
            skip=skip,
            limit=limit,
            sort=sort,
            projection_model=projection_model,
            session=session,
        )

    @classmethod
    def all(
        cls,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        sort: Union[None, str, List[Tuple[str, SortDirection]]] = None,
        projection_model: Optional[Type[BaseModel]] = None,
        session: Optional[ClientSession] = None,
    ) -> FindMany:
        """
        the same as find_all
        """
        return cls.find_all(
            skip=skip,
            limit=limit,
            sort=sort,
            projection_model=projection_model,
            session=session,
        )

    async def replace(
        self, session: Optional[ClientSession] = None
    ) -> "Document":
        """
        Fully update the document in the database

        :param session: Optional[ClientSession] - pymongo session.
        :return: None
        """
        if self.id is None:
            raise DocumentWasNotSaved

        await self.find_one({"_id": self.id}).replace_one(
            self, session=session
        )
        return self

    @classmethod
    async def replace_many(
        cls,
        documents: List["Document"],
        session: Optional[ClientSession] = None,
    ) -> None:
        """
        Replace list of documents

        :param documents: List["Document"]
        :param session: Optional[ClientSession] - pymongo session.
        :return: None
        """
        ids_list = [document.id for document in documents]
        if await cls.find(In(cls.id, ids_list)).count() != len(ids_list):
            raise ReplaceError(
                "Some of the documents are not exist in the collection"
            )
        await cls.find(In(cls.id, ids_list), session=session).delete()
        await cls.insert_many(documents, keep_ids=True, session=session)

    async def update(
        self, *args, session: Optional[ClientSession] = None
    ) -> None:
        """
        Partially update the document in the database

        :param args: *Union[dict, Mapping] - the modifications to apply.
        :param session: ClientSession - pymongo session.
        :return: None
        """
        await self.find_one({"_id": self.id}).update(*args, session=session)
        await self._sync()

    @classmethod
    def update_all(
        cls,
        *args: Union[dict, Mapping],
        session: Optional[ClientSession] = None,
    ) -> UpdateResult:
        """
        Partially update all the documents

        :param args: *Union[dict, Mapping] - the modifications to apply.
        :param session: ClientSession - pymongo session.
        :return: UpdateResult - pymongo UpdateResult instance
        """
        return cls.find_all().update_many(*args, session=session)

    async def delete(
        self, session: Optional[ClientSession] = None
    ) -> DeleteResult:
        """
        Delete the document

        :param session: Optional[ClientSession] - pymongo session.
        :return: DeleteResult - pymongo DeleteResult instance.
        """
        return await self.find_one({"_id": self.id}).delete(session=session)

    @classmethod
    async def delete_all(
        cls, session: Optional[ClientSession] = None
    ) -> DeleteResult:
        """
        Delete all the documents

        :param session: Optional[ClientSession] - pymongo session.
        :return: DeleteResult - pymongo DeleteResult instance.
        """
        return await cls.find_all().delete(session=session)

    @classmethod
    def aggregate(
        cls,
        aggregation_pipeline: list,
        aggregation_model: Type[BaseModel] = None,
        session: Optional[ClientSession] = None,
    ) -> AggregationQuery:
        """
        Aggregate over collection.
        Returns [AggregationQuery](/api/queries/#aggregationquery) query object
        :param aggregation_pipeline: list - aggregation pipeline
        :param aggregation_model: Type[BaseModel]
        :param session: Optional[ClientSession]
        :return: [AggregationQuery](/api/queries/#aggregationquery)
        """
        return cls.find_all().aggregate(
            aggregation_pipeline=aggregation_pipeline,
            projection_model=aggregation_model,
            session=session,
        )

    @classmethod
    async def count(cls) -> int:
        """
        Number of documents in the collections
        The same as find_all().count()

        :return: int
        """
        return await cls.find_all().count()

    @classmethod
    async def init_collection(
        cls, database: AsyncIOMotorDatabase, allow_index_dropping: bool
    ) -> None:
        """
        Internal CollectionMeta class creator

        :param database: AsyncIOMotorDatabase - motor database instance
        :param allow_index_dropping: bool - if index dropping is allowed
        :return: None
        """
        collection_class = getattr(cls, "Collection", None)
        collection_meta = await collection_factory(
            database=database,
            document_model=cls,
            allow_index_dropping=allow_index_dropping,
            collection_class=collection_class,
        )
        setattr(cls, "CollectionMeta", collection_meta)

        for k, v in cls.__fields__.items():
            path = v.alias or v.name
            setattr(cls, k, ExpressionField(path))

    @classmethod
    def _get_collection_meta(cls) -> Type:
        """
        Get internal CollectionMeta class, which was created on
        the collection initialization step

        :return: CollectionMeta class
        """
        collection_meta = getattr(cls, "CollectionMeta", None)
        if collection_meta is None:
            raise CollectionWasNotInitialized
        return collection_meta

    @classmethod
    def get_motor_collection(cls) -> AsyncIOMotorCollection:
        """
        Get Motor Collection to access low level control

        :return: AsyncIOMotorCollection
        """
        collection_meta = cls._get_collection_meta()
        return collection_meta.motor_collection

    @classmethod
    async def inspect_collection(
        cls, session: Optional[ClientSession] = None
    ) -> InspectionResult:
        """
        Check, if documents, stored in the MongoDB collection
        are compatible with the Document schema

        :return: InspectionResult
        """
        inspection_result = InspectionResult()
        async for json_document in cls.get_motor_collection().find(
            {}, session=session
        ):
            try:
                cls.parse_obj(json_document)
            except ValidationError as e:
                if inspection_result.status == InspectionStatuses.OK:
                    inspection_result.status = InspectionStatuses.FAIL
                inspection_result.errors.append(
                    InspectionError(
                        document_id=json_document["_id"], error=str(e)
                    )
                )
        return inspection_result

    class Config:
        json_encoders = {
            ObjectId: lambda v: str(v),
        }
        allow_population_by_field_name = True
